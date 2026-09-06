"""Run all data fetch and analysis scripts in order."""

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT = SCRIPTS_DIR.parent
PROCESSED_DIR = _ROOT / "data" / "processed"

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "unknown"


def _lookback_days() -> int:
    raw = os.environ.get("LOOKBACK_DAYS", "7")
    try:
        value = int(raw)
    except ValueError:
        return 7
    return value if value >= 1 else 7


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
            entry["plan_name"] = p.get("plan_name")
            entry["phase"] = p.get("phase")
            entry["phase_start"] = p.get("start")
            entry["phase_end"] = p.get("end")
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


def _readiness_signal(name: str, contribution: int | None, reason: str) -> dict:
    if contribution is None:
        status = "unavailable"
        score = 0
    else:
        status = "positive" if contribution > 0 else "adverse" if contribution < 0 else "neutral"
        score = contribution
    return {
        "name": name,
        "status": status,
        "contribution": score,
        "reason": reason,
    }


def _relative_change_pct(current: object, baseline: object) -> float | None:
    try:
        current_value = float(current)
        baseline_value = float(baseline)
    except (TypeError, ValueError):
        return None
    if baseline_value <= 0:
        return None
    return (current_value - baseline_value) / baseline_value * 100.0


def _trend_signal(
    name: str,
    trend: dict | None,
    moderate_threshold: float,
    strong_threshold: float,
    inverse: bool = False,
) -> dict:
    if not isinstance(trend, dict):
        return _readiness_signal(name, None, f"No {name.replace('_', ' ')} trend is available.")

    change_pct = _relative_change_pct(trend.get("current"), trend.get("avg_7d"))
    if change_pct is None:
        return _readiness_signal(name, None, f"No usable {name.replace('_', ' ')} baseline is available.")

    effective_change = -change_pct if inverse else change_pct
    if effective_change <= -strong_threshold:
        contribution = -2
    elif effective_change <= -moderate_threshold:
        contribution = -1
    elif effective_change >= strong_threshold:
        contribution = 2
    elif effective_change >= moderate_threshold:
        contribution = 1
    else:
        contribution = 0

    trend_label = trend.get("trend_7d")
    favorable_trend = "down" if inverse else "up"
    adverse_trend = "up" if inverse else "down"
    if trend_label == favorable_trend:
        contribution = min(2, contribution + 1)
    elif trend_label == adverse_trend:
        contribution = max(-2, contribution - 1)

    direction = "above" if change_pct > 0 else "below" if change_pct < 0 else "at"
    reason = (
        f"{name.replace('_', ' ').title()} is {abs(change_pct):.1f}% {direction} "
        f"its 7-day average and trending {trend_label or 'is unavailable'}."
    )
    return _readiness_signal(name, contribution, reason)


def _sleep_signal(metrics: dict) -> dict:
    sleep_secs = metrics.get("sleep_secs")
    quality = metrics.get("sleep_quality")
    try:
        sleep_hours = float(sleep_secs) / 3600.0 if sleep_secs is not None else None
    except (TypeError, ValueError):
        sleep_hours = None
    quality_label = str(quality).upper() if quality is not None else None

    if sleep_hours is None and quality_label is None:
        return _readiness_signal("sleep", None, "No sleep data is available.")
    if quality_label == "POOR" or (sleep_hours is not None and sleep_hours < 6.0):
        contribution = -2
    elif quality_label == "AVG" or (sleep_hours is not None and sleep_hours < 7.0):
        contribution = -1
    elif quality_label in {"GOOD", "GREAT"} or (sleep_hours is not None and sleep_hours >= 7.0):
        contribution = 1
    else:
        contribution = 0

    duration = f"{sleep_hours:.1f} hours" if sleep_hours is not None else "unknown duration"
    return _readiness_signal(
        "sleep",
        contribution,
        f"Sleep was {duration} with {quality_label or 'unknown'} quality.",
    )


def compute_training_readiness(metrics: dict | None, week_summary: dict | None) -> dict:
    """Combine current form, recovery, and intensity recency into a daily readiness signal."""
    metrics = metrics if isinstance(metrics, dict) else {}
    week_summary = week_summary if isinstance(week_summary, dict) else {}
    signals: list[dict] = []
    hard_vetoes: list[str] = []
    readiness_caps: list[str] = []

    ctl = week_summary.get("ctl")
    atl = week_summary.get("atl")
    form_zone = week_summary.get("form_zone")
    try:
        has_form = float(ctl) > 0 and atl is not None and form_zone is not None
    except (TypeError, ValueError):
        has_form = False
    if has_form:
        form_contributions = {
            "transition": 1,
            "fresh": 2,
            "grey_zone": 1,
            "optimal": 0,
            "high_risk": -3,
        }
        contribution = form_contributions.get(str(form_zone), 0)
        form_pct = week_summary.get("form_percent_display")
        form_display = f" ({form_pct:.1f}%)" if isinstance(form_pct, (int, float)) else ""
        signals.append(_readiness_signal("form", contribution, f"Form is {form_zone}{form_display}."))
        if form_zone == "high_risk":
            hard_vetoes.append("Form is in the high-risk zone.")
    else:
        signals.append(_readiness_signal("form", None, "No usable CTL, ATL, and form data is available."))

    days_since_hard = week_summary.get("days_since_last_hard_session")
    if isinstance(days_since_hard, (int, float)) and days_since_hard >= 0:
        days = int(days_since_hard)
        if days == 0:
            contribution = -3
            hard_vetoes.append("A hard session was completed today.")
        elif days == 1:
            contribution = -1
            readiness_caps.append("A hard session was completed one day ago; readiness is capped at yellow.")
        elif days == 2:
            contribution = 1
        else:
            contribution = 2
        signals.append(
            _readiness_signal(
                "hard_session_recency",
                contribution,
                f"The last hard session was {days} day{'s' if days != 1 else ''} ago.",
            )
        )
    else:
        signals.append(
            _readiness_signal("hard_session_recency", None, "No recent hard-session date is available.")
        )

    wellness = metrics.get("wellness_trends")
    wellness = wellness if isinstance(wellness, dict) else {}
    signals.append(_trend_signal("hrv", wellness.get("hrv"), 5.0, 10.0))
    signals.append(_trend_signal("resting_hr", wellness.get("resting_hr"), 3.0, 7.0, inverse=True))
    signals.append(_sleep_signal(metrics))

    recovery_adverse = sum(
        1
        for signal in signals
        if signal["name"] in {"hrv", "resting_hr", "sleep"} and signal["contribution"] < 0
    )
    if recovery_adverse >= 2:
        hard_vetoes.append("At least two recovery signals are adverse.")

    available_signals = [signal for signal in signals if signal["status"] != "unavailable"]
    score = sum(signal["contribution"] for signal in available_signals)
    available_count = len(available_signals)
    confidence = "high" if available_count >= 4 else "medium" if available_count >= 2 else "low"

    if not available_signals:
        status = "unknown"
    elif hard_vetoes or score <= -3:
        status = "red"
    elif score >= 2:
        status = "green"
    else:
        status = "yellow"
    if readiness_caps and status == "green":
        status = "yellow"

    recommendations = {
        "green": "The planned hard session is acceptable if subjective readiness is also good.",
        "yellow": "Adjust training load and verify recovery before adding intensity.",
        "red": "Avoid hard training and prioritize recovery.",
        "unknown": "Assess readiness manually before prescribing intensity.",
    }
    return {
        "status": status,
        "score": score,
        "confidence": confidence,
        "recommendation": recommendations[status],
        "reasons": [signal["reason"] for signal in available_signals],
        "safety_vetoes": hard_vetoes + readiness_caps,
        "signals": signals,
    }


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
