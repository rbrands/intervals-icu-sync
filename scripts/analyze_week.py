"""Analyze the latest week of cycling training data from data/raw/."""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def load_data() -> list:
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print("Error: No JSON files found in data/raw/.")
        sys.exit(1)
    latest = json_files[-1]
    print(f"Loading {latest.name}")
    return json.loads(latest.read_text())


def _current_week_range() -> tuple[date, date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def filter_activities(activities: list) -> list:
    monday, sunday = _current_week_range()
    result = []
    for a in activities:
        if (
            a.get("type") == "Ride"
            and a.get("source") != "STRAVA"
            and a.get("icu_training_load") is not None
            and a.get("icu_training_load", 0) > 30
        ):
            start = a.get("start_date_local", "")[:10]
            try:
                activity_date = date.fromisoformat(start)
            except ValueError:
                continue
            if monday <= activity_date <= sunday:
                result.append(a)
    return result


def _classify_ride(activity: dict) -> str:
    raw = activity.get("interval_summary") or ""
    summary = " ".join(raw) if isinstance(raw, list) else raw
    if re.search(r"\b(1m|2m|3m|4m)\b", summary) or "110%" in summary:
        return "vo2max"
    if re.search(r"\b(10m|12m|20m)\b", summary):
        return "threshold"
    return "endurance"


def compute_metrics(activities: list) -> dict:
    total_load = sum(a.get("icu_training_load", 0) for a in activities)
    times = [a.get("moving_time", 0) / 3600 for a in activities]
    total_time = sum(times)
    longest = max(times, default=0.0)

    vo2_sessions = 0
    threshold_sessions = 0
    endurance_sessions = 0
    for a in activities:
        category = _classify_ride(a)
        if category == "vo2max":
            vo2_sessions += 1
        elif category == "threshold":
            threshold_sessions += 1
        else:
            endurance_sessions += 1

    decouplings = [
        float(a["decoupling"])
        for a in activities
        if a.get("decoupling") is not None
    ]
    avg_decoupling = sum(decouplings) / len(decouplings) if decouplings else 0.0
    high_decoupling = sum(1 for d in decouplings if d > 10)

    return {
        "total_training_load": total_load,
        "number_of_rides": len(activities),
        "total_time_hours": total_time,
        "longest_ride_hours": longest,
        "vo2_sessions": vo2_sessions,
        "threshold_sessions": threshold_sessions,
        "endurance_sessions": endurance_sessions,
        "avg_decoupling": avg_decoupling,
        "high_decoupling_rides": high_decoupling,
    }


def print_report(metrics: dict) -> None:
    m = metrics
    print()
    print("=== Weekly Training Summary ===")
    print(f"Total Load:          {m['total_training_load']}")
    print(f"Number of Rides:     {m['number_of_rides']}")
    print(f"Total Time (h):      {m['total_time_hours']:.1f}")
    print(f"Longest Ride (h):    {m['longest_ride_hours']:.1f}")
    print()
    print("Distribution:")
    print(f"  VO2max sessions:     {m['vo2_sessions']}")
    print(f"  Threshold sessions:  {m['threshold_sessions']}")
    print(f"  Endurance sessions:  {m['endurance_sessions']}")
    print()
    print("Decoupling:")
    print(f"  Average:                    {m['avg_decoupling']:.1f}%")
    print(f"  High decoupling rides (>10%): {m['high_decoupling_rides']}")
    print()
    print("=== Coaching Interpretation ===")

    load = m["total_training_load"]
    if load < 250:
        print("Load:       Low load week")
    elif load <= 450:
        print("Load:       Moderate load week")
    else:
        print("Load:       High load week")

    if m["vo2_sessions"] == 0:
        print("Intensity:  Missing high intensity work")
    if m["threshold_sessions"] == 0:
        print("Intensity:  Missing threshold work")
    if m["endurance_sessions"] == 0:
        print("Volume:     Missing endurance volume")

    if m["avg_decoupling"] > 8:
        print("Aerobic:    Aerobic endurance or fueling needs improvement")


def main() -> None:
    monday, sunday = _current_week_range()
    print(f"Calendar week: {monday.isoformat()} – {sunday.isoformat()}")
    activities = load_data()
    rides = filter_activities(activities)
    if not rides:
        print("No qualifying rides found.")
        sys.exit(0)
    metrics = compute_metrics(rides)
    print_report(metrics)


if __name__ == "__main__":
    main()
