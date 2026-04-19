"""Fetch current athlete performance metrics from intervals.icu and save to data/processed/metrics_{date}.json."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.config import API_KEY, ATHLETE_ID
import requests

BASE_URL = "https://intervals.icu/api/v1"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def fetch_athlete_info() -> dict:
    r = requests.get(f"{BASE_URL}/athlete/{ATHLETE_ID}", auth=("API_KEY", API_KEY), timeout=10)
    r.raise_for_status()
    data = r.json()
    result = {"weight": data.get("icu_weight")}
    dob_str = data.get("icu_date_of_birth")
    if dob_str:
        from datetime import date as _date
        dob = _date.fromisoformat(dob_str)
        today = date.today()
        result["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    else:
        result["age"] = None
    sex_raw = data.get("sex")
    result["sex"] = {"M": "Male", "F": "Female"}.get(sex_raw) if sex_raw else None
    return result


def fetch_wellness() -> dict:
    today = date.today()
    # Fetch last 30 days to find most recent values that may not be set today
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness",
        auth=("API_KEY", API_KEY),
        params={"oldest": (today - timedelta(days=30)).isoformat(), "newest": today.isoformat()},
        timeout=10,
    )
    r.raise_for_status()
    entries = r.json()

    # Use today's entry for CTL/ATL/HRV, but fall back to last known value for vo2max
    today_entry = next((e for e in reversed(entries) if e.get("id") == today.isoformat()), {})
    last_vo2max = next((e["vo2max"] for e in reversed(entries) if e.get("vo2max") is not None), None)

    sport_info = next((s for s in (today_entry.get("sportInfo") or []) if s.get("type") == "Ride"), {})
    return {
        "ctl": today_entry.get("ctl"),
        "atl": today_entry.get("atl"),
        "resting_hr": today_entry.get("restingHR"),
        "hrv": today_entry.get("hrv"),
        "eftp": sport_info.get("eftp"),
        "w_prime_wellness": sport_info.get("wPrime"),
    }


def fetch_metrics_from_activities() -> dict:
    today = date.today()
    oldest = (today - timedelta(days=30)).isoformat()
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/activities",
        auth=("API_KEY", API_KEY),
        params={"oldest": oldest, "newest": today.isoformat()},
        timeout=10,
    )
    r.raise_for_status()
    activities = r.json()

    for activity in activities:
        if activity.get("icu_ftp"):
            return {
                "ftp": activity.get("icu_ftp"),
                "rolling_ftp": activity.get("icu_rolling_ftp"),
                "w_prime": activity.get("icu_w_prime"),
                "rolling_w_prime": activity.get("icu_rolling_w_prime"),
                "rolling_p_max": activity.get("icu_rolling_p_max"),
            }
    return {}


def fetch_5min_power() -> float | None:
    """Fetch best 5-minute power from the 42-day power curve (matches intervals.icu UI)."""
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/power-curves",
        auth=("API_KEY", API_KEY),
        params={"type": "Ride", "curves": "42d"},
        timeout=10,
    )
    r.raise_for_status()
    curves = r.json().get("list", [])
    if not curves:
        return None
    secs = curves[0].get("secs", [])
    watts = curves[0].get("watts", [])
    idx = next((i for i, s in enumerate(secs) if s == 300), None)
    return watts[idx] if idx is not None else None


def calc_vo2max_from_power(p5min_watts: float, weight_kg: float) -> float:
    """intervals.icu formula: 16.6 + (8.87 × 5min_power / weight)"""
    return round(16.6 + (8.87 * p5min_watts / weight_kg), 1)


def main() -> None:
    if not API_KEY:
        print("Error: INTERVALS_API_KEY is not set.")
        sys.exit(1)
    if not ATHLETE_ID:
        print("Error: ATHLETE_ID is not set.")
        sys.exit(1)

    today = date.today()
    metrics = {"date": today.isoformat()}
    metrics.update(fetch_metrics_from_activities())
    metrics.update(fetch_athlete_info())
    metrics.update(fetch_wellness())

    p5min = fetch_5min_power()
    metrics["p5min"] = p5min
    if p5min and metrics.get("weight"):
        metrics["vo2max"] = calc_vo2max_from_power(p5min, metrics["weight"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"metrics_{today.isoformat()}.json"
    output_file.write_text(json.dumps(metrics, indent=2))

    print(f"Date:         {metrics['date']}")
    print(f"FTP:          {metrics.get('ftp')} W")
    print(f"Rolling FTP:  {metrics.get('rolling_ftp')} W")
    print(f"eFTP:         {metrics.get('eftp'):.1f} W" if metrics.get("eftp") else "eFTP:         n/a")
    print(f"W':           {metrics.get('w_prime')} J")
    print(f"5min power:   {metrics.get('p5min')} W (42-day best)")
    print(f"VO2Max:       {metrics.get('vo2max')} (intervals.icu formula)")
    print(f"Age:          {metrics.get('age')} years")
    print(f"Weight:       {metrics.get('weight')} kg")
    print(f"CTL:          {metrics.get('ctl'):.1f}" if metrics.get("ctl") else "CTL:          n/a")
    print(f"ATL:          {metrics.get('atl'):.1f}" if metrics.get("atl") else "ATL:          n/a")
    print(f"Saved to:     {output_file}")


if __name__ == "__main__":
    main()
