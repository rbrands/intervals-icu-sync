"""Run all data fetch and analysis scripts in order."""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPTS_DIR.parent / "data" / "processed"


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


def _load_json(path: Path) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text())
    return None


def _extract_ride_plan_summary(plan_data: dict | None) -> dict | None:
    """Return Ride-only phase and load target from training plan data."""
    if not plan_data:
        return None
    phases = [
        p for p in (plan_data.get("active_phases") or [])
        if p.get("sport_type") == "Ride"
    ]
    targets = [
        t for t in (plan_data.get("weekly_load_targets") or [])
        if t.get("sport_type") == "Ride"
    ]
    if not phases and not targets:
        return None
    result: dict = {}
    if phases:
        p = phases[0]
        result["plan_name"] = p.get("plan_name")
        result["phase"] = p.get("phase")
        result["phase_start"] = p.get("start")
        result["phase_end"] = p.get("end")
    if targets:
        result["weekly_load_target"] = targets[0].get("load_target")
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

    # Embed Ride training plan info into week_summary
    ride_plan = _extract_ride_plan_summary(plan_data)
    if ride_plan and isinstance(week_data, dict):
        week_data["training_plan"] = ride_plan

    # coach_input is currently a flat list of activities
    activities = activities_data if isinstance(activities_data, list) else (activities_data or {}).get("activities")

    coach_input = {
        "week_starting": monday_str,
        "metrics": metrics,
        "week_summary": week_data,
        "activities": activities,
        "fueling_analysis": fueling_data,
    }

    output_file = PROCESSED_DIR / f"coach_input_{monday_str}.json"
    output_file.write_text(json.dumps(coach_input, indent=2))
    print(f"\nConsolidated coach_input saved to: {output_file.name}")


def main() -> None:
    run("get_activities.py")
    run("get_metrics.py")
    run("get_training_plan.py")
    run("prepare_activities_for_coach.py")
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
