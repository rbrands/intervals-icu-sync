"""Fetch activities from intervals.icu for the last 7 days and save to data/raw/."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running the script directly without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.client import get_activities
from intervals_icu.config import API_KEY, ATHLETE_ID

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    if not API_KEY:
        print("Error: INTERVALS_API_KEY is not set. Copy .env.example to .env and fill in your key.")
        sys.exit(1)
    if not ATHLETE_ID:
        print("Error: ATHLETE_ID is not set. Copy .env.example to .env and fill in your athlete ID.")
        sys.exit(1)

    end_date = date.today() + timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    activities = get_activities(
        api_key=API_KEY,
        athlete_id=ATHLETE_ID,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    # Filter activities to only include those from Garmin Connect
    activities = [
        a for a in activities
        if a.get("source") == "GARMIN_CONNECT"
        and a.get("type") == "Ride"
        and a.get("icu_weighted_avg_watts") is not None
        and a.get("icu_training_load", 0) > 20
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / f"activities_{end_date.isoformat()}.json"
    output_file.write_text(json.dumps(activities, indent=2))

    print(f"Saved {len(activities)} activities to {output_file}")


if __name__ == "__main__":
    main()
