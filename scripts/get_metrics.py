"""Fetch current athlete performance metrics from intervals.icu and save to data/processed/metrics_{date}.json."""

import json
import math
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
            w_prime = activity.get("icu_w_prime")
            rolling_w_prime = activity.get("icu_rolling_w_prime")
            if not w_prime and rolling_w_prime is not None:
                w_prime = rolling_w_prime

            return {
                "ftp": activity.get("icu_ftp"),
                "rolling_ftp": activity.get("icu_rolling_ftp"),
                "w_prime": w_prime,
                "rolling_w_prime": rolling_w_prime,
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

_POWER_PROFILE_TYPE_LABELS: dict[str, str] = {
    "all_rounder": "All Rounder",
    "puncheur": "Puncheur",
    "sprinter": "Sprinter",
    "climber": "Climber",
    "time_trialist": "Time Trialist",
}

# Heuristic archetypes for a simple rider-type estimate from power profile features.
_POWER_PROFILE_TYPE_PROTOTYPES: dict[str, dict[str, float]] = {
    "all_rounder": {
        "sprint_ratio": 1.9,
        "anaerobic_ratio": 1.34,
        "punch_ratio": 1.18,
        "p20_wkg": 3.3,
        "curve_slope": -0.54,
    },
    "puncheur": {
        "sprint_ratio": 2.05,
        "anaerobic_ratio": 1.45,
        "punch_ratio": 1.22,
        "p20_wkg": 3.5,
        "curve_slope": -0.5,
    },
    "sprinter": {
        "sprint_ratio": 2.25,
        "anaerobic_ratio": 1.6,
        "punch_ratio": 1.3,
        "p20_wkg": 3.2,
        "curve_slope": -0.46,
    },
    "climber": {
        "sprint_ratio": 1.55,
        "anaerobic_ratio": 1.2,
        "punch_ratio": 1.14,
        "p20_wkg": 4.3,
        "curve_slope": -0.6,
    },
    "time_trialist": {
        "sprint_ratio": 1.65,
        "anaerobic_ratio": 1.18,
        "punch_ratio": 1.12,
        "p20_wkg": 4.0,
        "curve_slope": -0.62,
    },
}

_POWER_PROFILE_FEATURE_WEIGHTS: dict[str, float] = {
    "sprint_ratio": 1.2,
    "anaerobic_ratio": 1.2,
    "punch_ratio": 1.0,
    "p20_wkg": 0.35,
    "curve_slope": 0.8,
}

_POWER_PROFILE_FEATURE_SCALES: dict[str, float] = {
    "sprint_ratio": 0.30,
    "anaerobic_ratio": 0.22,
    "punch_ratio": 0.12,
    "p20_wkg": 1.25,
    "curve_slope": 0.12,
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


_VO2MAX_BANDS: dict[str, dict[str, dict[str, float]]] = {
    "male": {
        "teen_13_19": {
            "very_poor_max": 35.0,
            "poor_min": 35.0,
            "poor_max": 38.3,
            "average_min": 38.4,
            "average_max": 45.1,
            "good_min": 45.2,
            "good_max": 50.9,
            "very_good_min": 51.0,
            "very_good_max": 55.9,
            "excellent_min": 56.0,
        },
        "adult_20_29": {
            "very_poor_max": 33.0,
            "poor_min": 33.0,
            "poor_max": 36.4,
            "average_min": 36.6,
            "average_max": 42.4,
            "good_min": 42.5,
            "good_max": 46.4,
            "very_good_min": 46.5,
            "very_good_max": 52.4,
            "excellent_min": 52.5,
        },
        "master_30_39": {
            "very_poor_max": 31.5,
            "poor_min": 31.5,
            "poor_max": 35.4,
            "average_min": 35.5,
            "average_max": 40.9,
            "good_min": 41.0,
            "good_max": 44.9,
            "very_good_min": 45.0,
            "very_good_max": 49.4,
            "excellent_min": 49.5,
        },
        "master_40_49": {
            "very_poor_max": 30.2,
            "poor_min": 30.2,
            "poor_max": 33.5,
            "average_min": 33.6,
            "average_max": 38.9,
            "good_min": 39.0,
            "good_max": 43.7,
            "very_good_min": 43.8,
            "very_good_max": 48.0,
            "excellent_min": 48.1,
        },
        "grand_master_50_59": {
            "very_poor_max": 26.1,
            "poor_min": 26.1,
            "poor_max": 30.9,
            "average_min": 31.0,
            "average_max": 35.7,
            "good_min": 35.8,
            "good_max": 40.9,
            "very_good_min": 41.0,
            "very_good_max": 45.3,
            "excellent_min": 45.4,
        },
        "senior_60_plus": {
            "very_poor_max": 20.5,
            "poor_min": 20.5,
            "poor_max": 26.0,
            "average_min": 26.1,
            "average_max": 32.2,
            "good_min": 32.3,
            "good_max": 36.4,
            "very_good_min": 36.5,
            "very_good_max": 44.2,
            "excellent_min": 44.3,
        },
    },
    "female": {
        "teen_13_19": {
            "very_poor_max": 25.0,
            "poor_min": 25.0,
            "poor_max": 30.9,
            "average_min": 31.0,
            "average_max": 34.9,
            "good_min": 35.0,
            "good_max": 38.9,
            "very_good_min": 39.0,
            "very_good_max": 41.9,
            "excellent_min": 42.0,
        },
        "adult_20_29": {
            "very_poor_max": 23.6,
            "poor_min": 23.6,
            "poor_max": 28.9,
            "average_min": 29.0,
            "average_max": 32.9,
            "good_min": 33.0,
            "good_max": 36.9,
            "very_good_min": 37.0,
            "very_good_max": 41.0,
            "excellent_min": 41.1,
        },
        "master_30_39": {
            "very_poor_max": 22.8,
            "poor_min": 22.8,
            "poor_max": 26.9,
            "average_min": 27.0,
            "average_max": 31.4,
            "good_min": 31.5,
            "good_max": 35.6,
            "very_good_min": 35.7,
            "very_good_max": 40.0,
            "excellent_min": 40.1,
        },
        "master_40_49": {
            "very_poor_max": 21.0,
            "poor_min": 21.0,
            "poor_max": 24.4,
            "average_min": 24.5,
            "average_max": 28.9,
            "good_min": 29.0,
            "good_max": 32.8,
            "very_good_min": 32.9,
            "very_good_max": 36.9,
            "excellent_min": 37.0,
        },
        "grand_master_50_59": {
            "very_poor_max": 20.2,
            "poor_min": 20.2,
            "poor_max": 22.7,
            "average_min": 22.8,
            "average_max": 26.9,
            "good_min": 27.0,
            "good_max": 31.4,
            "very_good_min": 31.5,
            "very_good_max": 35.7,
            "excellent_min": 35.8,
        },
        "senior_60_plus": {
            "very_poor_max": 17.5,
            "poor_min": 17.5,
            "poor_max": 20.1,
            "average_min": 20.2,
            "average_max": 24.4,
            "good_min": 24.5,
            "good_max": 30.2,
            "very_good_min": 30.3,
            "very_good_max": 31.4,
            "excellent_min": 31.5,
        },
    },
}


def fetch_power_profile() -> dict:
    """Fetch best-effort power for key durations from the 42-day power curve.

    Returns a dict with keys p15s, p30s, p1min, p3min, p5min, p20min.
    Each value is a dict with 'watts' (int) and 'w_per_kg' (float).
    Also includes 'period_days' (int) and 'curve_slope' (float) for the modelled
    power-over-time slope on a log-log scale (less negative = more anaerobic),
    and a heuristic rider type estimate under: 'type', 'type_key',
    'heuristic_score', 'type_scores', and 'type_method'.
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

    profile_type = _build_power_profile_type(profile)
    if profile_type:
        profile.update(profile_type)

    return profile


def _safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    num = _to_float(numerator)
    den = _to_float(denominator)
    if num is None or den is None or den <= 0:
        return None
    return round(num / den, 4)


def _build_power_profile_type(power_profile: dict) -> dict | None:
    p15 = ((power_profile.get("p15s") or {}).get("watts"))
    p1 = ((power_profile.get("p1min") or {}).get("watts"))
    p5 = ((power_profile.get("p5min") or {}).get("watts"))
    p20 = ((power_profile.get("p20min") or {}).get("watts"))
    p20_wkg = ((power_profile.get("p20min") or {}).get("w_per_kg"))
    slope = _to_float(power_profile.get("curve_slope"))

    features: dict[str, float] = {
        "sprint_ratio": _safe_ratio(p15, p20),
        "anaerobic_ratio": _safe_ratio(p1, p20),
        "punch_ratio": _safe_ratio(p5, p20),
        "p20_wkg": _to_float(p20_wkg),
        "curve_slope": slope,
    }

    available_feature_count = sum(1 for value in features.values() if value is not None)
    if available_feature_count < 3:
        return None

    similarities: dict[str, float] = {}
    for type_key, prototype in _POWER_PROFILE_TYPE_PROTOTYPES.items():
        weighted_distance = 0.0
        total_weight = 0.0
        for feature_name, target_value in prototype.items():
            value = features.get(feature_name)
            if value is None:
                continue
            scale = _POWER_PROFILE_FEATURE_SCALES[feature_name]
            weight = _POWER_PROFILE_FEATURE_WEIGHTS[feature_name]
            weighted_distance += weight * abs(value - target_value) / scale
            total_weight += weight

        if total_weight <= 0:
            continue

        normalized_distance = weighted_distance / total_weight
        similarities[type_key] = math.exp(-normalized_distance)

    if not similarities:
        return None

    similarity_sum = sum(similarities.values())
    if similarity_sum <= 0:
        return None

    probabilities = {
        key: round(value / similarity_sum, 3)
        for key, value in similarities.items()
    }
    winner_key = max(probabilities, key=probabilities.get)
    winner_label = _POWER_PROFILE_TYPE_LABELS.get(winner_key, winner_key)

    return {
        "type": winner_label,
        "type_key": winner_key,
        "heuristic_score": probabilities[winner_key],
        "type_scores": probabilities,
        "type_method": "heuristic_v1",
    }


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
    """Age group for FTP classification."""
    if age is None:
        return None
    if age >= 60:
        return "senior_60_plus"
    if age >= 50:
        return "grand_master_50_59"
    if age >= 40:
        return "master_40_49"
    return "elite_18_39"


def _age_group_slug_vo2max(age: int | None) -> str | None:
    """Age group for VO2max classification."""
    if age is None:
        return None
    if age >= 60:
        return "senior_60_plus"
    if age >= 50:
        return "grand_master_50_59"
    if age >= 40:
        return "master_40_49"
    if age >= 30:
        return "master_30_39"
    if age >= 20:
        return "adult_20_29"
    return "teen_13_19"


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


def _build_vo2max_classification(
    vo2max: float | int | None,
    age: int | None,
    sex: str | None,
) -> dict | None:
    """Classify VO2max based on age, sex, and ml/kg/min value.
    
    Returns category, category_range, next_category, and delta_to_next.
    """
    vo2_val = _to_float(vo2max)
    sex_slug = _normalize_sex_label(sex)
    age_group = _age_group_slug_vo2max(age)

    if vo2_val is None or vo2_val <= 0 or sex_slug is None or age_group is None:
        return None

    bands = _VO2MAX_BANDS[sex_slug][age_group]

    # Determine category
    category = "excellent"
    min_v = bands["excellent_min"]
    max_v = None

    if vo2_val <= bands["very_poor_max"]:
        category = "very_poor"
        min_v = None
        max_v = bands["very_poor_max"]
    elif vo2_val <= bands["poor_max"]:
        category = "poor"
        min_v = bands["poor_min"]
        max_v = bands["poor_max"]
    elif vo2_val <= bands["average_max"]:
        category = "average"
        min_v = bands["average_min"]
        max_v = bands["average_max"]
    elif vo2_val <= bands["good_max"]:
        category = "good"
        min_v = bands["good_min"]
        max_v = bands["good_max"]
    elif vo2_val <= bands["very_good_max"]:
        category = "very_good"
        min_v = bands["very_good_min"]
        max_v = bands["very_good_max"]

    # Calculate next category
    thresholds: list[tuple[str, float]] = [
        ("very_poor", 0.0),
        ("poor", bands["poor_min"]),
        ("average", bands["average_min"]),
        ("good", bands["good_min"]),
        ("very_good", bands["very_good_min"]),
        ("excellent", bands["excellent_min"]),
    ]

    current_idx = next((i for i, (name, _) in enumerate(thresholds) if name == category), None)
    next_category = None
    delta_to_next = None
    if current_idx is not None and current_idx + 1 < len(thresholds):
        next_category = thresholds[current_idx + 1][0]
        next_min = thresholds[current_idx + 1][1]
        delta_to_next = round(max(0.0, next_min - vo2_val), 1)

    return {
        "ml_per_kg_min": round(vo2_val, 1),
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
    vo2max = None
    if p5min and metrics.get("weight"):
        vo2max = calc_vo2max_from_power(p5min, metrics["weight"])
    
    metrics["vo2max_classification"] = _build_vo2max_classification(
        vo2max,
        metrics.get("age"),
        metrics.get("sex"),
    )

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
    vo2_class = metrics.get("vo2max_classification") or {}
    if vo2_class.get("ml_per_kg_min") is not None:
        print(f"VO2Max:       {vo2_class.get('ml_per_kg_min')} ml/kg/min (intervals.icu formula)")
    else:
        print("VO2Max:       n/a")
    if vo2_class.get("category"):
        print(f"VO2Max Class: {vo2_class.get('category')} ({vo2_class.get('age_group')}, {vo2_class.get('sex')})")
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
    if power_profile.get("type"):
        print(
            "  Type:   "
            f"{power_profile.get('type')} "
            f"(heuristic_score {power_profile.get('heuristic_score')})"
        )
    print(f"Saved to:     {output_file}")


if __name__ == "__main__":
    main()
