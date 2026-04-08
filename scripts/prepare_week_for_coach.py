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
