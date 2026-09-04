"""Fetch activities from intervals.icu for the current calendar week (Mon–today) and save to data/raw."""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running the script directly without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.client import get_activities
from intervals_icu.config import API_KEY, ATHLETE_ID

_DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DATA_DIR = Path(os.environ.get("INTERVALS_RAW_DIR", str(_DEFAULT_RAW_DIR)))


def _as_float(value: object, default: float = 0.0) -> float:
    """Convert API values to float safely (None/invalid -> default)."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


_METRIC_FIELDS = (
    "icu_training_load",
    "icu_average_watts",
    "icu_weighted_avg_watts",
    "average_watts",
    "average_heartrate",
    "avg_hr",
)

_SUPPORTED_ACTIVITY_TYPES = {
    "Ride",
    "VirtualRide",
    "MountainBikeRide",
    "GravelRide",
    "Run",
    "TrailRun",
    "VirtualRun",
}

_RUN_ACTIVITY_TYPES = {"Run", "TrailRun", "VirtualRun"}


def _has_training_load(activity: dict) -> bool:
    """True when intervals.icu supplied a training load value."""
    return activity.get("icu_training_load") is not None


def _passes_load_filter(activity: dict) -> bool:
    """Return True when an activity should be kept by load/metric rules."""
    if activity.get("type") in _RUN_ACTIVITY_TYPES and _has_training_load(activity):
        return True
    return (
        _as_float(activity.get("icu_training_load")) > 20
        or (bool(activity.get("tags")) and _has_usable_metrics(activity))
    )


def _has_usable_metrics(activity: dict) -> bool:
    """True when an activity carries at least one analyzable metric."""
    if any(activity.get(field) is not None for field in _METRIC_FIELDS):
        return True
    return bool(activity.get("icu_zone_times") or activity.get("icu_hr_zone_times"))


def main() -> None:
    if not API_KEY:
        print("Error: INTERVALS_API_KEY is not set. Copy .env.example to .env and fill in your key.")
        sys.exit(1)
    if not ATHLETE_ID:
        print("Error: ATHLETE_ID is not set. Copy .env.example to .env and fill in your athlete ID.")
        sys.exit(1)

    today = date.today()
    start_date = today - timedelta(days=today.weekday() + 7)  # Monday of previous week
    end_date = today

    activities = get_activities(
        api_key=API_KEY,
        athlete_id=ATHLETE_ID,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    # Filter activities: cycling rides and runs with meaningful training load;
    # exclude Strava duplicates.
    # Tagged activities below the load threshold are kept only when they carry usable
    # metrics, so empty placeholder entries do not reach the coach.
    activities = [
        a for a in activities
        if a.get("type") in _SUPPORTED_ACTIVITY_TYPES
        and a.get("source") != "STRAVA"
        and _passes_load_filter(a)
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / f"activities_{end_date.isoformat()}.json"
    output_file.write_text(json.dumps(activities, indent=2))

    print(f"Saved {len(activities)} activities to {output_file}")


if __name__ == "__main__":
    main()
