"""Fetch current athlete performance metrics from intervals.icu and save to data/processed/metrics_{date}.json."""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.config import API_KEY, ATHLETE_ID
import requests

BASE_URL = "https://intervals.icu/api/v1"
_DEFAULT_PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
OUTPUT_DIR = Path(os.environ.get("INTERVALS_PROCESSED_DIR", str(_DEFAULT_PROCESSED_DIR)))


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


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _entry_date(entry: dict) -> date | None:
    raw_id = entry.get("id")
    if not isinstance(raw_id, str):
        return None
    try:
        return date.fromisoformat(raw_id[:10])
    except ValueError:
        return None


def _window_values(
    series: list[tuple[date, float]],
    end_date: date,
    days: int,
    offset_days: int = 0,
) -> list[float]:
    window_end = end_date - timedelta(days=offset_days)
    window_start = window_end - timedelta(days=days - 1)
    return [value for point_date, value in series if window_start <= point_date <= window_end]


def _trend_label(delta: float | None, stable_threshold: float) -> str | None:
    if delta is None:
        return None
    if abs(delta) < stable_threshold:
        return "stable"
    return "up" if delta > 0 else "down"


def _build_metric_trend(entries: list[dict], source_key: str, stable_threshold: float) -> dict | None:
    today = date.today()

    daily_values: dict[date, float] = {}
    for entry in entries:
        point_date = _entry_date(entry)
        if point_date is None or point_date > today:
            continue
        value = _to_float(entry.get(source_key))
        if value is not None:
            daily_values[point_date] = value

    if not daily_values:
        return None

    series = sorted(daily_values.items())
    latest_date, current = series[-1]

    values_7d = _window_values(series, latest_date, 7)
    prev_7d = _window_values(series, latest_date, 7, offset_days=7)

    avg_7d = round(sum(values_7d) / len(values_7d), 2) if values_7d else None
    prev_7d_avg = round(sum(prev_7d) / len(prev_7d), 2) if prev_7d else None
    delta_vs_prev_7d = (
        round(avg_7d - prev_7d_avg, 2)
        if avg_7d is not None and prev_7d_avg is not None
        else None
    )

    return {
        "current": round(current, 2),
        "avg_7d": avg_7d,
        "avg_prev_7d": prev_7d_avg,
        "trend_7d": _trend_label(delta_vs_prev_7d, stable_threshold),
    }


def _empty_metric_trend() -> dict:
    return {
        "current": None,
        "avg_7d": None,
        "avg_prev_7d": None,
        "trend_7d": None,
    }


def _build_wellness_trends(entries: list[dict]) -> dict:
    metric_specs: list[tuple[str, str, float]] = [
        ("weight", "weight", 0.2),
        ("resting_hr", "restingHR", 1.0),
        ("hrv", "hrv", 2.0),
    ]

    trends: dict = {}
    for metric_name, source_key, stable_threshold in metric_specs:
        trend = _build_metric_trend(
            entries,
            source_key=source_key,
            stable_threshold=stable_threshold,
        )
        trends[metric_name] = trend if trend is not None else _empty_metric_trend()
    return trends


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

    # Use today's entry for day-specific readiness metrics and derive trends
    # from the full 30-day wellness history.
    today_entry = next((e for e in reversed(entries) if e.get("id") == today.isoformat()), {})

    _SLEEP_QUALITY_LABELS = {1: "GREAT", 2: "GOOD", 3: "AVG", 4: "POOR"}

    sport_info = next((s for s in (today_entry.get("sportInfo") or []) if s.get("type") == "Ride"), {})
    raw_sleep_quality = today_entry.get("sleepQuality")
    return {
        "ctl": today_entry.get("ctl"),
        "atl": today_entry.get("atl"),
        "resting_hr": today_entry.get("restingHR"),
        "hrv": today_entry.get("hrv"),
        "eftp": sport_info.get("eftp"),
        "w_prime_wellness": sport_info.get("wPrime"),
        "sleep_secs": today_entry.get("sleepSecs"),
        "sleep_quality": _SLEEP_QUALITY_LABELS.get(raw_sleep_quality, raw_sleep_quality),
        "wellness_trends": _build_wellness_trends(entries),
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
                "lthr": activity.get("lthr"),
                "max_hr": activity.get("athlete_max_hr"),
            }
    return {}


_POWER_PROFILE_TARGETS: dict[int, str] = {
    15: "p15s",
    30: "p30s",
    60: "p1min",
    180: "p3min",
    300: "p5min",
    1200: "p20min",
}

_FTP_BANDS: dict[str, dict[str, dict[str, float | None]]] = {
    "male": {
        "elite_18_39": {
            "beginner_max": 2.5,
            "recreational_min": 2.5,
            "recreational_max": 3.5,
            "ambitious_min": 3.5,
            "ambitious_max": 4.5,
            "performance_min": 4.5,
            "performance_max": 5.0,
            "elite_min": 5.0,
            "pro_min": 5.5,
            "pro_max": 6.5,
        },
        "master_40_49": {
            "beginner_max": 2.3,
            "recreational_min": 2.3,
            "recreational_max": 3.3,
            "ambitious_min": 3.3,
            "ambitious_max": 4.3,
            "performance_min": 4.3,
            "performance_max": 4.8,
            "elite_min": 4.8,
            "pro_min": None,
            "pro_max": None,
        },
        "grand_master_50_59": {
            "beginner_max": 2.1,
            "recreational_min": 2.1,
            "recreational_max": 3.1,
            "ambitious_min": 3.1,
            "ambitious_max": 4.1,
            "performance_min": 4.1,
            "performance_max": 4.6,
            "elite_min": 4.6,
            "pro_min": None,
            "pro_max": None,
        },
        "senior_60_plus": {
            "beginner_max": 2.0,
            "recreational_min": 2.0,
            "recreational_max": 2.9,
            "ambitious_min": 2.9,
            "ambitious_max": 3.9,
            "performance_min": 3.9,
            "performance_max": 4.4,
            "elite_min": 4.4,
            "pro_min": None,
            "pro_max": None,
        },
    },
    "female": {
        "elite_18_39": {
            "beginner_max": 2.3,
            "recreational_min": 2.3,
            "recreational_max": 3.2,
            "ambitious_min": 3.2,
            "ambitious_max": 4.2,
            "performance_min": 4.2,
            "performance_max": 4.8,
            "elite_min": 4.8,
            "pro_min": 4.8,
            "pro_max": 6.0,
        },
        "master_40_49": {
            "beginner_max": 2.1,
            "recreational_min": 2.1,
            "recreational_max": 3.0,
            "ambitious_min": 3.0,
            "ambitious_max": 4.0,
            "performance_min": 4.0,
            "performance_max": 4.6,
            "elite_min": 4.6,
            "pro_min": None,
            "pro_max": None,
        },
        "grand_master_50_59": {
            "beginner_max": 2.0,
            "recreational_min": 2.0,
            "recreational_max": 2.8,
            "ambitious_min": 2.8,
            "ambitious_max": 3.8,
            "performance_min": 3.8,
            "performance_max": 4.4,
            "elite_min": 4.4,
            "pro_min": None,
            "pro_max": None,
        },
        "senior_60_plus": {
            "beginner_max": 1.8,
            "recreational_min": 1.8,
            "recreational_max": 2.6,
            "ambitious_min": 2.6,
            "ambitious_max": 3.6,
            "performance_min": 3.6,
            "performance_max": 4.2,
            "elite_min": 4.2,
            "pro_min": None,
            "pro_max": None,
        },
    },
}


def fetch_power_profile() -> dict:
    """Fetch best-effort power for key durations from the 42-day power curve.

    Returns a dict with keys p15s, p30s, p1min, p3min, p5min, p20min.
    Each value is a dict with 'watts' (int) and 'w_per_kg' (float).
    Also includes 'period_days' (int) and 'curve_slope' (float) for the modelled
    power-over-time slope on a log-log scale (less negative = more anaerobic).
    """
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/power-curves",
        auth=("API_KEY", API_KEY),
        params={"type": "Ride", "curves": "42d"},
        timeout=10,
    )
    r.raise_for_status()
    curves = r.json().get("list", [])
    if not curves:
        return {}

    curve = curves[0]
    secs: list[int] = curve.get("secs", [])
    watts: list[int] = curve.get("watts", [])
    wkg: list[float] = curve.get("watts_per_kg", [])

    profile: dict = {}
    for target_sec, key in _POWER_PROFILE_TARGETS.items():
        if target_sec in secs:
            i = secs.index(target_sec)
        else:
            # Fall back to closest available duration
            i = min(range(len(secs)), key=lambda x: abs(secs[x] - target_sec))
        w = watts[i] if i < len(watts) else None
        wk = wkg[i] if i < len(wkg) else None
        profile[key] = {
            "watts": w,
            "w_per_kg": round(wk, 2) if wk is not None else None,
        }

    map_plot = curve.get("mapPlot", {})
    slope = map_plot.get("poSlope")
    profile["curve_slope"] = round(slope, 4) if slope is not None else None
    profile["period_days"] = curve.get("days")

    return profile


def calc_vo2max_from_power(p5min_watts: float, weight_kg: float) -> float:
    """intervals.icu formula: 16.6 + (8.87 × 5min_power / weight)"""
    return round(16.6 + (8.87 * p5min_watts / weight_kg), 1)


def _calc_wkg(power_watts: float | int | None, weight_kg: float | int | None) -> float | None:
    power = _to_float(power_watts)
    weight = _to_float(weight_kg)
    if power is None or weight is None or weight <= 0:
        return None
    return round(power / weight, 2)


def _normalize_sex_label(value: str | None) -> str | None:
    if not value:
        return None
    norm = value.strip().lower()
    if norm in {"male", "m"}:
        return "male"
    if norm in {"female", "f"}:
        return "female"
    return None


def _age_group_slug(age: int | None) -> str | None:
    if age is None:
        return None
    if age >= 60:
        return "senior_60_plus"
    if age >= 50:
        return "grand_master_50_59"
    if age >= 40:
        return "master_40_49"
    return "elite_18_39"


def _build_ftp_classification(
    ftp_wkg: float | int | None,
    age: int | None,
    sex: str | None,
) -> dict | None:
    wkg = _to_float(ftp_wkg)
    sex_slug = _normalize_sex_label(sex)
    age_group = _age_group_slug(age)

    if wkg is None or wkg <= 0 or sex_slug is None or age_group is None:
        return None

    bands = _FTP_BANDS[sex_slug][age_group]

    category = "elite"
    min_v = bands["elite_min"]
    max_v = None

    if wkg < bands["beginner_max"]:
        category = "beginner"
        min_v = None
        max_v = bands["beginner_max"]
    elif wkg < bands["recreational_max"]:
        category = "recreational"
        min_v = bands["recreational_min"]
        max_v = bands["recreational_max"]
    elif wkg < bands["ambitious_max"]:
        category = "ambitious_amateur"
        min_v = bands["ambitious_min"]
        max_v = bands["ambitious_max"]
    elif wkg < bands["performance_max"]:
        category = "performance_oriented"
        min_v = bands["performance_min"]
        max_v = bands["performance_max"]

    pro_min = bands["pro_min"]
    pro_max = bands["pro_max"]
    if pro_min is not None and wkg >= pro_min and (pro_max is None or wkg <= pro_max):
        category = "pro"
        min_v = pro_min
        max_v = pro_max

    thresholds: list[tuple[str, float]] = [
        ("recreational", bands["recreational_min"]),
        ("ambitious_amateur", bands["ambitious_min"]),
        ("performance_oriented", bands["performance_min"]),
        ("elite", bands["elite_min"]),
    ]
    if pro_min is not None:
        thresholds.append(("pro", pro_min))

    current_idx = next((i for i, (name, _) in enumerate(thresholds) if name == category), None)
    next_category = None
    delta_to_next = None
    if current_idx is not None and current_idx + 1 < len(thresholds):
        next_category = thresholds[current_idx + 1][0]
        next_min = thresholds[current_idx + 1][1]
        delta_to_next = round(max(0.0, next_min - wkg), 2)

    return {
        "w_per_kg": round(wkg, 2),
        "age_group": age_group,
        "sex": sex_slug,
        "category": category,
        "category_range": {
            "min": min_v,
            "max": max_v,
        },
        "next_category": next_category,
        "delta_to_next": delta_to_next,
    }


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

    ftp_wkg = _calc_wkg(metrics.get("ftp"), metrics.get("weight"))
    metrics["ftp_classification"] = _build_ftp_classification(
        ftp_wkg,
        metrics.get("age"),
        metrics.get("sex"),
    )

    power_profile = fetch_power_profile()
    metrics["power_profile"] = power_profile
    p5min = (power_profile.get("p5min") or {}).get("watts")
    if p5min and metrics.get("weight"):
        metrics["vo2max"] = calc_vo2max_from_power(p5min, metrics["weight"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"metrics_{today.isoformat()}.json"
    output_file.write_text(json.dumps(metrics, indent=2))

    print(f"Date:         {metrics['date']}")
    print(f"FTP:          {metrics.get('ftp')} W")
    ftp_class = metrics.get("ftp_classification") or {}
    if ftp_class.get("w_per_kg") is not None:
        print(f"FTP (W/kg):   {ftp_class.get('w_per_kg'):.2f}")
    else:
        print("FTP (W/kg):   n/a")
    if ftp_class.get("category"):
        print(f"FTP Class:    {ftp_class.get('category')} ({ftp_class.get('age_group')}, {ftp_class.get('sex')})")
    print(f"Rolling FTP:  {metrics.get('rolling_ftp')} W")
    print(f"eFTP:         {metrics.get('eftp'):.1f} W" if metrics.get("eftp") else "eFTP:         n/a")
    print(f"W':           {metrics.get('w_prime')} J")
    print(f"VO2Max:       {metrics.get('vo2max')} (intervals.icu formula)")
    print(f"Age:          {metrics.get('age')} years")
    print(f"Weight:       {metrics.get('weight')} kg")
    print(f"CTL:          {metrics.get('ctl'):.1f}" if metrics.get("ctl") else "CTL:          n/a")
    print(f"ATL:          {metrics.get('atl'):.1f}" if metrics.get("atl") else "ATL:          n/a")
    print()
    print("Power Profile (42-day best):")
    for key, label in [("p15s", "15s"), ("p30s", "30s"), ("p1min", "1min"), ("p3min", "3min"), ("p5min", "5min"), ("p20min", "20min")]:
        entry = power_profile.get(key, {})
        w = entry.get("watts")
        wkg = entry.get("w_per_kg")
        if w:
            print(f"  {label:>5}: {w} W  ({wkg} w/kg)")
    print(f"  Slope:  {power_profile.get('curve_slope')} (log-log, less negative = more anaerobic)")
    print(f"Saved to:     {output_file}")


if __name__ == "__main__":
    main()
