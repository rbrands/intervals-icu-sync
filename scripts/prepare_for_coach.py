"""Read latest activities JSON from data/raw and output a simplified JSON for coach analysis."""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "coach_input.json"


def load_data() -> list:
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print("Error: No JSON files found in data/raw/.")
        sys.exit(1)
    latest = json_files[-1]
    print(f"Loading {latest.name}")
    return json.loads(latest.read_text())


def filter_activities(activities: list) -> list:
    return [
        a for a in activities
        if a.get("type") == "Ride"
        and a.get("source") != "STRAVA"
        and a.get("icu_training_load", 0) > 30
    ]


def extract_fields(activity: dict) -> dict:
    return {
        "date": (activity.get("start_date_local") or "")[:10],
        "name": activity.get("name"),
        "duration_hours": round((activity.get("moving_time") or 0) / 3600, 2),
        "training_load": activity.get("icu_training_load"),
        "avg_power": activity.get("icu_average_watts"),
        "norm_power": activity.get("icu_weighted_avg_watts"),
        "interval_summary": activity.get("interval_summary"),
        "decoupling": activity.get("decoupling"),
        "rpe": activity.get("icu_rpe"),
    }


def main() -> None:
    activities = load_data()
    rides = filter_activities(activities)
    rides.sort(key=lambda a: (a.get("start_date_local") or ""))
    output = [extract_fields(a) for a in rides]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    total_load = sum(a["training_load"] or 0 for a in output)
    print(f"Rides:       {len(output)}")
    print(f"Total load:  {total_load}")
    print(f"Saved to:    {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
