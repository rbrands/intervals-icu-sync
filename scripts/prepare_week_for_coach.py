"""Run all data fetch and analysis scripts in order."""

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.training_readiness import annotate_hard_sessions, compute_training_readiness
from intervals_icu.strength import (
    CANONICAL_STRENGTH_TAGS, STRENGTH_PHASE_BY_TAG, STRENGTH_PHASE_MAX_SESSIONS,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT = SCRIPTS_DIR.parent
PROCESSED_DIR = _ROOT / "data" / "processed"

STRENGTH_HISTORY_WEEKS = 16

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "unknown"


def _lookback_days() -> int:
    raw = os.environ.get("LOOKBACK_DAYS", "7")
    try:
        value = int(raw)
    except ValueError:
        return 7
    return value if value >= 1 else 7


def _strength_history_weeks() -> int:
    raw = os.environ.get("STRENGTH_HISTORY_WEEKS", str(STRENGTH_HISTORY_WEEKS))
    try:
        value = int(raw)
    except ValueError:
        return STRENGTH_HISTORY_WEEKS
    return value if value >= 1 else STRENGTH_HISTORY_WEEKS


def _canonical_strength_tags(tags: object) -> list[str]:
    if not isinstance(tags, list):
        return []
    return [tag for tag in tags if isinstance(tag, str) and tag in CANONICAL_STRENGTH_TAGS]


def _optional_number(value: object) -> int | float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def build_strength_history(
    completed_activities: list[dict],
    planned_events: list[dict],
) -> list[dict]:
    """Resolve activity/planned tags, then infer from a recent anchored session."""
    planned_tags_by_date: dict[str, list[str]] = {}
    planned_weeks: set[tuple[int, int]] = set()
    for event in planned_events:
        if event.get("type") not in (None, "WeightTraining"):
            continue
        event_date = (event.get("start_date_local") or event.get("date") or "")[:10]
        if not event_date:
            continue
        planned_weeks.add(date.fromisoformat(event_date).isocalendar()[:2])
        tags = _canonical_strength_tags(event.get("tags"))
        if tags:
            target = planned_tags_by_date.setdefault(event_date, [])
            target.extend(tag for tag in tags if tag not in target)

    history = []
    for activity in sorted(
        completed_activities,
        key=lambda activity: activity.get("start_date_local") or "",
        reverse=True,
    ):
        if (
            activity.get("type") != "WeightTraining"
            or activity.get("source") == "STRAVA"
        ):
            continue
        session_date = (activity.get("start_date_local") or "")[:10]
        if not session_date:
            continue
        session_day = date.fromisoformat(session_date)
        session_week = session_day.isocalendar()[:2]

        tags = _canonical_strength_tags(activity.get("tags"))
        if tags:
            phase_source = "activity"
        else:
            tags = planned_tags_by_date.get(session_date, [])
            phase_source = "planned" if tags else "none"
            if not tags:
                candidates = [
                    planned_date
                    for planned_date in planned_tags_by_date
                    if date.fromisoformat(planned_date).isocalendar()[:2] == session_week
                ]
                if candidates:
                    closest_date = min(
                        candidates,
                        key=lambda day: (
                            abs((date.fromisoformat(day) - session_day).days),
                            day,
                        ),
                    )
                    tags = planned_tags_by_date[closest_date]
                    phase_source = "planned_week"

        moving_time = _optional_number(activity.get("moving_time")) or 0
        history.append(
            {
                "id": activity.get("id"),
                "date": session_date,
                "tags": list(tags),
                "phase_source": phase_source,
                "planned_week_exists": session_week in planned_weeks,
                "duration_minutes": int((moving_time + 30) // 60),
                "training_load": _optional_number(activity.get("icu_training_load")),
                "rpe": _optional_number(activity.get("icu_rpe")),
            }
        )

    anchor = None
    for row in reversed(history):
        if row["phase_source"] != "none":
            anchor = row
        elif anchor is not None:
            gap = (date.fromisoformat(row["date"]) - date.fromisoformat(anchor["date"])).days
            if gap < 21:
                row["tags"] = list(anchor["tags"])
                row["phase_source"] = "inferred"

    return history


def annotate_strength_phases(activities: list[dict], strength_history: list[dict]) -> list[dict]:
    """Attach resolved phases without changing activity tags or exporting history."""
    by_id = {
        str(row["id"]): row for row in strength_history if row.get("id") is not None
    }
    annotated = []
    for activity in activities:
        entry = dict(activity)
        if entry.get("type") == "WeightTraining":
            row = by_id.get(str(entry.get("id")))
            if row is not None:
                entry["strength_phase"] = next(
                    (STRENGTH_PHASE_BY_TAG[tag] for tag in row["tags"]
                     if tag in STRENGTH_PHASE_BY_TAG), None,
                )
                entry["strength_phase_source"] = row["phase_source"]
                entry["strength_tagging_reminder_needed"] = (
                    row["phase_source"] in ("none", "inferred")
                    and not row.get("planned_week_exists", False)
                )
        annotated.append(entry)
    return annotated


def build_strength_week_summary(
    strength_history: list[dict],
    today: date,
    week_summary: dict,
) -> dict:
    """Summarize strength phase continuity and reuse weekly per-sport totals."""
    history = sorted(strength_history, key=lambda row: row.get("date", ""), reverse=True)
    latest = history[0] if history else None
    latest_date = None
    if latest:
        try:
            latest_date = date.fromisoformat(latest["date"])
        except (KeyError, TypeError, ValueError):
            latest_date = None
    days_since = (today - latest_date).days if latest_date else None

    current_phase = None
    phase_started = None
    phase_session_count = 0
    if days_since is None or days_since < 21:
        previous_day = latest_date
        for row in history:
            session_day = date.fromisoformat(row["date"])
            if previous_day is not None and (previous_day - session_day).days >= 21:
                break
            previous_day = session_day
            if row.get("phase_source") == "none":
                continue
            phase = next(
                (
                    STRENGTH_PHASE_BY_TAG[tag]
                    for tag in row.get("tags", [])
                    if tag in STRENGTH_PHASE_BY_TAG
                ),
                None,
            )
            if phase is None:
                continue
            if current_phase is None:
                current_phase = phase
            if phase != current_phase:
                break
            phase_started = row.get("date")
            phase_session_count += 1

    phase_targets = {
        "adaptation": "4-6",
        "transition": "2-3",
        "maximum": "8-12",
        "maintenance": "ongoing",
    }
    phase_maximum = STRENGTH_PHASE_MAX_SESSIONS.get(current_phase)
    current_monday = today - timedelta(days=today.weekday())
    sessions_per_week = [0, 0, 0, 0]
    tagging_reminder_needed = False
    first_week = current_monday - timedelta(weeks=4)
    for row in history:
        session_date = date.fromisoformat(row["date"])
        if first_week <= session_date < current_monday:
            sessions_per_week[(session_date - first_week).days // 7] += 1
        if (
            current_monday - timedelta(weeks=1) <= session_date <= today
            and row.get("phase_source") in ("none", "inferred")
            and not row.get("planned_week_exists", False)
        ):
            tagging_reminder_needed = True
    return {
        "current_phase": current_phase,
        "phase_started": phase_started,
        "phase_session_count": phase_session_count,
        "phase_target_sessions": phase_targets.get(current_phase),
        "phase_overdue": phase_maximum is not None and phase_session_count > phase_maximum,
        "sessions_this_week": week_summary.get("strength_sessions", 0),
        "days_since_last_strength": days_since,
        "last_session_tags": list(latest.get("tags", [])) if latest else [],
        "weekly_strength_load": week_summary.get("strength_load", 0),
        "sessions_per_week_last_4": sessions_per_week,
        "untagged_sessions_last_16_weeks": sum(
            row.get("phase_source") == "none" for row in history
        ),
        "inferred_sessions_last_16_weeks": sum(
            row.get("phase_source") == "inferred" for row in history
        ),
        "tagging_reminder_needed": tagging_reminder_needed,
    }


def fetch_strength_history(
    today: date,
    *,
    api_key: str | None = None,
    athlete_id: str | None = None,
) -> list[dict]:
    """Fetch projected strength activities and planned events for recent history."""
    from intervals_icu.client import (
        get_planned_strength_events,
        get_strength_history_activities,
    )
    if api_key is None or athlete_id is None:
        from intervals_icu.config import API_KEY, ATHLETE_ID

        api_key = API_KEY if api_key is None else api_key
        athlete_id = ATHLETE_ID if athlete_id is None else athlete_id

    oldest_day = today - timedelta(weeks=_strength_history_weeks())
    oldest = oldest_day.isoformat()
    newest = today.isoformat()
    completed = get_strength_history_activities(api_key, athlete_id, oldest, newest)
    planned_oldest = (oldest_day - timedelta(days=oldest_day.weekday())).isoformat()
    planned_newest = (today + timedelta(days=6 - today.weekday())).isoformat()
    planned = get_planned_strength_events(
        api_key, athlete_id, planned_oldest, planned_newest,
    )
    return build_strength_history(completed, planned)


def run(script: str, extra_env: dict[str, str] | None = None) -> None:
    print(f"\n{'=' * 50}")
    print(f"Running {script} ...")
    print("=" * 50)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        check=False,
        env=env,
    )
    if result.returncode != 0:
        print(f"\nERROR: {script} failed with exit code {result.returncode}. Aborting.")
        sys.exit(result.returncode)


def _normalize_tag_value(value: str) -> str:
    return value.replace("treshold", "threshold")


def _normalize_tags(data: object) -> object:
    """Normalize legacy tag spelling in loaded JSON payloads.

    Only `tag` and `tags` fields are rewritten to avoid changing unrelated text.
    """
    if isinstance(data, dict):
        normalized: dict = {}
        for key, value in data.items():
            if key == "tag" and isinstance(value, str):
                normalized[key] = _normalize_tag_value(value)
            elif key == "tags" and isinstance(value, list):
                normalized[key] = [
                    _normalize_tag_value(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                normalized[key] = _normalize_tags(value)
        return normalized
    if isinstance(data, list):
        return [_normalize_tags(item) for item in data]
    return data


def _load_json(path: Path) -> dict | list | None:
    if path.exists():
        return _normalize_tags(json.loads(path.read_text(encoding="utf-8")))
    return None


def _extract_ride_plan_summary(plan_data: dict | None, monday: date) -> list[dict]:
    """Return list of Ride-only plan entries for current and next week."""
    if not plan_data:
        return []
    phases = [
        p for p in (plan_data.get("active_phases") or [])
        if p.get("sport_type") == "Ride"
    ]

    next_week_phases = [
        p for p in (plan_data.get("next_week_active_phases") or [])
        if p.get("sport_type") == "Ride"
    ]

    def _copy_target_fields(entry: dict, target: dict) -> None:
        load_target = target.get("load_target")
        time_target_hours = target.get("time_target_hours")
        if load_target is not None:
            entry["weekly_load_target"] = load_target
        if time_target_hours is not None:
            entry["weekly_time_target_hours"] = time_target_hours

    def _build_entry(targets_key: str, constraints_key: str, week_monday: date, phase_list: list) -> dict | None:
        targets = [
            t for t in (plan_data.get(targets_key) or [])
            if t.get("sport_type") == "Ride"
        ]
        week_constraints = plan_data.get(constraints_key) or []
        if not phase_list and not targets and not week_constraints:
            return None
        entry: dict = {"week": week_monday.isoformat()}
        if phase_list:
            p = phase_list[0]
            if p.get("phase") is not None:
                entry["phase"] = p["phase"]
        if targets:
            _copy_target_fields(entry, targets[0])
            entry["week_type"] = targets[0].get("week_type", "NORMAL")
            if targets[0].get("week_note"):
                entry["week_note"] = targets[0]["week_note"]
        if week_constraints:
            entry["day_constraints"] = week_constraints
        return entry

    result: list[dict] = []
    current = _build_entry("weekly_load_targets", "weekly_day_constraints", monday, phases)
    if current:
        result.append(current)
    next_week = _build_entry(
        "next_week_load_targets",
        "next_week_day_constraints",
        monday + timedelta(weeks=1),
        next_week_phases,
    )
    if next_week:
        result.append(next_week)
    return result


def _merge_fueling_into_activities(
    activities: list[dict] | None,
    fueling_data: dict | None,
) -> tuple[list[dict], dict | None]:
    activity_list = activities if isinstance(activities, list) else []

    fueling_by_date: dict[str, list[dict]] = {}
    cleaned_fueling = fueling_data
    if isinstance(fueling_data, dict):
        fueling_activities = fueling_data.get("activities")
        if isinstance(fueling_activities, list):
            for entry in fueling_activities:
                if not isinstance(entry, dict):
                    continue
                entry_date = entry.get("date")
                if not isinstance(entry_date, str):
                    continue
                fueling_by_date.setdefault(entry_date, []).append(entry)
        cleaned_fueling = {k: v for k, v in fueling_data.items() if k != "activities"}

    merged_activities: list[dict] = []
    for activity in activity_list:
        if activity.get("type") == "WeightTraining":
            merged_activities.append(dict(activity))
            continue

        date_key = activity.get("date")
        queue = fueling_by_date.get(date_key, []) if isinstance(date_key, str) else []
        fueling_match = queue.pop(0) if queue else None
        if isinstance(fueling_match, dict):
            fueling_match = {
                k: v
                for k, v in fueling_match.items()
                if k not in {"date", "name", "duration_hours"}
            }
        merged = dict(activity)
        merged["fueling"] = fueling_match
        merged_activities.append(merged)

    return merged_activities, cleaned_fueling


def merge_training_load_history(
    load_history: list[dict] | None,
    readiness_history: list[dict] | None,
) -> list[dict]:
    """Combine weekly TSS data with compact CTL/ATL/form snapshots."""
    readiness_by_week = {
        entry.get("week_starting"): entry
        for entry in (readiness_history or [])
        if isinstance(entry, dict) and isinstance(entry.get("week_starting"), str)
    }
    merged_history: list[dict] = []

    for entry in load_history or []:
        if not isinstance(entry, dict):
            continue
        merged_entry = dict(entry)
        readiness = readiness_by_week.pop(entry.get("week_starting"), None)
        if readiness:
            for key in ("ctl", "atl", "form_absolute", "form_pct", "form_percent_display"):
                merged_entry[key] = readiness.get(key)
        merged_history.append(merged_entry)

    return merged_history + list(readiness_by_week.values())


def consolidate() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.isoformat()
    lookback_days = _lookback_days()

    # Locate metrics file (uses today's date)
    metrics_files = sorted(PROCESSED_DIR.glob("metrics_*.json"))
    metrics = json.loads(metrics_files[-1].read_text()) if metrics_files else None

    activities_data = _load_json(PROCESSED_DIR / f"coach_input_{monday_str}.json")
    fueling_data = _load_json(PROCESSED_DIR / f"fueling_analysis_{monday_str}.json")
    week_data = _load_json(PROCESSED_DIR / f"week_summary_{monday_str}.json")
    plan_data = _load_json(PROCESSED_DIR / f"training_plan_{today.isoformat()}.json")
    planned_workouts_data = _load_json(PROCESSED_DIR / f"planned_workouts_{monday_str}.json")

    # Keep readiness metrics in week_summary only (no duplication in metrics).
    ctl = None
    atl = None
    readiness_history = None
    if isinstance(metrics, dict):
        ctl = metrics.pop("ctl", None)
        atl = metrics.pop("atl", None)
        readiness_history = metrics.pop("training_load_history", None)

    if not isinstance(week_data, dict):
        week_data = {}
    if week_data.get("ctl") is None and ctl is not None:
        week_data["ctl"] = ctl
    if week_data.get("atl") is None and atl is not None:
        week_data["atl"] = atl
    strength_history = fetch_strength_history(today)
    week_data["strength"] = build_strength_week_summary(
        strength_history,
        today,
        week_data,
    )
    week_data["training_readiness"] = compute_training_readiness(metrics, week_data)

    # Embed Ride training plan info into week_summary
    ride_plan = _extract_ride_plan_summary(plan_data, monday)
    if ride_plan:
        week_data["training_plan"] = ride_plan

    # coach_input is currently a flat list of activities
    activities = activities_data if isinstance(activities_data, list) else (activities_data or {}).get("activities")
    activities, fueling_data = _merge_fueling_into_activities(
        activities if isinstance(activities, list) else [],
        fueling_data if isinstance(fueling_data, dict) else None,
    )
    activities = annotate_strength_phases(activities, strength_history)
    activities = annotate_hard_sessions(activities, current_ctl=week_data.get("ctl"))

    coach_input = {
        "schema_version": _SCHEMA_VERSION,
        "week_starting": monday_str,
        "lookback_days": lookback_days,
        "current_date": date.today().isoformat(),
        "metrics": metrics,
        "week_summary": week_data,
        "training_load_history": merge_training_load_history(
            plan_data.get("training_load_history") if isinstance(plan_data, dict) else [],
            readiness_history if isinstance(readiness_history, list) else [],
        ),
        "activities": activities,
        "fueling_analysis": fueling_data,
        "planned_workouts": planned_workouts_data,
    }

    output_file = PROCESSED_DIR / f"coach_input_{monday_str}.json"
    output_file.write_text(json.dumps(coach_input, indent=2))
    print(f"\nConsolidated coach_input saved to: {output_file.name}")


def main() -> None:
    run("get_activities.py")
    run("get_metrics.py")
    run("get_training_plan.py")
    lookback_env = {"LOOKBACK_DAYS": str(_lookback_days())}
    run("prepare_activities_for_coach.py", extra_env=lookback_env)
    run("prepare_planned_workouts_for_coach.py")
    run("fueling_analysis.py", extra_env=lookback_env)
    run("analyze_week.py")
    print(f"\n{'=' * 50}")
    print("Consolidating all data into coach_input ...")
    print("=" * 50)
    consolidate()
    print(f"\n{'=' * 50}")
    print("All scripts completed successfully.")
    print("=" * 50)


if __name__ == "__main__":
    main()
