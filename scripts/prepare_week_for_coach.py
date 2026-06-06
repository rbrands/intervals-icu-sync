"""Run all data fetch and analysis scripts in order."""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT = SCRIPTS_DIR.parent
PROCESSED_DIR = _ROOT / "data" / "processed"

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "unknown"


def run(script: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"Running {script} ...")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        check=False,
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

    def _build_entry(targets_key: str, week_monday: date, phase_list: list) -> dict | None:
        targets = [
            t for t in (plan_data.get(targets_key) or [])
            if t.get("sport_type") == "Ride"
        ]
        if not phase_list and not targets:
            return None
        entry: dict = {"week": week_monday.isoformat()}
        if phase_list:
            p = phase_list[0]
            entry["plan_name"] = p.get("plan_name")
            entry["phase"] = p.get("phase")
            entry["phase_start"] = p.get("start")
            entry["phase_end"] = p.get("end")
        if targets:
            entry["weekly_load_target"] = targets[0].get("load_target")
            entry["week_type"] = targets[0].get("week_type", "NORMAL")
            entry["training_availability"] = targets[0].get("training_availability", "NORMAL")
            if targets[0].get("week_note"):
                entry["week_note"] = targets[0]["week_note"]
        return entry

    result: list[dict] = []
    current = _build_entry("weekly_load_targets", monday, phases)
    if current:
        result.append(current)
    next_week = _build_entry("next_week_load_targets", monday + timedelta(weeks=1), next_week_phases or phases)
    if next_week:
        result.append(next_week)
    return result


def consolidate() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.isoformat()

    # Locate metrics file (uses today's date)
    metrics_files = sorted(PROCESSED_DIR.glob("metrics_*.json"))
    metrics = json.loads(metrics_files[-1].read_text()) if metrics_files else None

    activities_data = _load_json(PROCESSED_DIR / f"coach_input_{monday_str}.json")
    fueling_data = _load_json(PROCESSED_DIR / f"fueling_analysis_{monday_str}.json")
    week_data = _load_json(PROCESSED_DIR / f"week_summary_{monday_str}.json")
    plan_data = _load_json(PROCESSED_DIR / f"training_plan_{today.isoformat()}.json")
    planned_workouts_data = _load_json(PROCESSED_DIR / f"planned_workouts_{monday_str}.json")

    # Embed Ride training plan info into week_summary
    ride_plan = _extract_ride_plan_summary(plan_data, monday)
    if ride_plan:
        if not isinstance(week_data, dict):
            week_data = {}
        week_data["training_plan"] = ride_plan

    # coach_input is currently a flat list of activities
    activities = activities_data if isinstance(activities_data, list) else (activities_data or {}).get("activities")

    coach_input = {
        "schema_version": _SCHEMA_VERSION,
        "week_starting": monday_str,
        "current_date": date.today().isoformat(),
        "metrics": metrics,
        "week_summary": week_data,
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
    run("prepare_activities_for_coach.py")
    run("prepare_planned_workouts_for_coach.py")
    run("fueling_analysis.py")
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
