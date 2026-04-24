"""Analyze carbohydrate fueling quality for cycling activities from coach_input JSON."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_data() -> list:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    input_file = DATA_DIR / f"coach_input_{monday.isoformat()}.json"
    if not input_file.exists():
        # Fall back to any coach_input file
        files = sorted(DATA_DIR.glob("coach_input_*.json"))
        if not files:
            print("Error: No coach_input JSON file found in data/processed/.")
            sys.exit(1)
        input_file = files[-1]
    print(f"Loading {input_file.name}\n")
    return json.loads(input_file.read_text())


def _classify_carbs_per_hour(carbs_per_hour: float) -> str:
    if carbs_per_hour < 40:
        return "very low"
    if carbs_per_hour < 60:
        return "low"
    if carbs_per_hour < 80:
        return "moderate"
    if carbs_per_hour <= 100:
        return "good"
    return "high"


def _classify_fueling_ratio(ratio: float) -> str:
    if ratio < 0.3:
        return "severe deficit"
    if ratio < 0.5:
        return "moderate deficit"
    if ratio <= 0.7:
        return "acceptable"
    return "good"


def _fueling_status(duration: float) -> str:
    if duration < 1.5:
        return "no fueling needed"
    if duration < 2.0:
        return "fueling optional"
    return "fueling required"


_STRUCTURED_INTERVAL_PATTERNS = [
    "5x", "6x", "4x", "3x", "8x", "10x",  # repetition notation
    "10m", "12m", "15m", "20m",             # long interval blocks
    "vo2", "threshold", "sweetspot",        # intensity labels
    "sst", "ftp",                           # common abbreviations
]


def _contains_structured_intervals(interval_summary) -> bool:
    if not interval_summary:
        return False
    text = interval_summary.lower() if isinstance(interval_summary, str) else " ".join(interval_summary).lower()
    return any(pattern in text for pattern in _STRUCTURED_INTERVAL_PATTERNS)


def _is_long_ride(duration: float, interval_summary) -> bool:
    return duration >= 2.5 and not _contains_structured_intervals(interval_summary)


_SHORT_INTERVAL_PATTERNS = ["2m", "3m", "4m", "5m"]
_LONG_INTERVAL_PATTERNS = ["8m", "10m", "12m", "15m", "20m"]
_SPRINT_PATTERNS = ["10s", "15s", "20s", "30s"]


def classify_ride(activity: dict) -> str:
    duration = activity.get("duration_hours") or 0
    z1_z2 = activity.get("z1_z2_pct") or 0
    z3_z4 = activity.get("z3_z4_pct") or 0
    z5_plus = activity.get("z5_plus_pct") or 0
    summary = activity.get("interval_summary") or ""
    if isinstance(summary, list):
        summary = " ".join(summary)
    summary_lower = summary.lower()

    has_long_intervals = any(p in summary_lower for p in _LONG_INTERVAL_PATTERNS)
    has_vo2_intervals = any(p in summary_lower for p in _SHORT_INTERVAL_PATTERNS)
    has_sprint_intervals = any(p in summary_lower for p in _SPRINT_PATTERNS)

    # 1. Long ride — highest priority
    if duration >= 2.5 and z1_z2 > 75:
        return "long_ride"

    # 2. Threshold — structured longer intervals with meaningful Z3+4 time
    if z3_z4 > 12 and has_long_intervals:
        return "threshold"

    # 3. VO2 — meaningful Z5+ time AND mid-length intervals (not sprints only)
    if z5_plus > 8 and has_vo2_intervals and not has_sprint_intervals:
        return "vo2"

    # 4. Sprint/neuromuscular — very short efforts with low Z5+ accumulation
    if has_sprint_intervals and z5_plus < 10:
        return "endurance_with_sprint"

    # 5. Recovery
    if duration < 1.5 and z1_z2 > 85:
        return "recovery"

    # 6. Default
    return "endurance"


def analyze_activity(activity: dict) -> dict:
    duration = activity.get("duration_hours") or 0
    carbs_ingested = activity.get("carbs_ingested_g") or 0
    carbs_used = activity.get("carbs_used_g") or 0
    decoupling = activity.get("decoupling") or 0
    rpe = activity.get("rpe") or 0
    interval_summary = activity.get("interval_summary")

    carbs_per_hour = carbs_ingested / duration if duration > 0 else 0
    fueling_ratio = carbs_ingested / carbs_used if carbs_used > 0 else None
    is_long = _is_long_ride(duration, interval_summary)

    if duration < 1.5:
        carbs_classification = "not required"
        ratio_classification = "not applicable"
    elif duration < 2.0:
        carbs_classification = "optional"
        ratio_classification = "optional"
    else:
        carbs_classification = _classify_carbs_per_hour(carbs_per_hour)
        ratio_classification = _classify_fueling_ratio(fueling_ratio) if fueling_ratio is not None else "n/a"

    flags = []
    if is_long and carbs_per_hour < 60:
        flags.append("underfueled long ride")
    if is_long and decoupling > 10 and carbs_per_hour < 60:
        flags.append("decoupling likely caused by low fueling")
    if is_long and rpe >= 8 and carbs_per_hour < 50:
        flags.append("high strain with low fueling")

    return {
        "date": activity.get("date"),
        "name": activity.get("name"),
        "duration_hours": duration,
        "ride_type": classify_ride(activity),
        "fueling_status": _fueling_status(duration),
        "carbs_per_hour": round(carbs_per_hour, 1),
        "fueling_ratio": round(fueling_ratio, 2) if fueling_ratio is not None else None,
        "carbs_classification": carbs_classification,
        "ratio_classification": ratio_classification,
        "is_long_ride": is_long,
        "flags": flags,
    }


def summarize_week(analyses: list) -> dict:
    long_rides = [a for a in analyses if a["is_long_ride"]]
    valid_cph = [a["carbs_per_hour"] for a in long_rides if a["carbs_per_hour"] > 0]
    valid_ratio = [a["fueling_ratio"] for a in long_rides if a["fueling_ratio"] is not None]
    underfueled = sum(1 for a in long_rides if "underfueled long ride" in a["flags"])

    return {
        "number_of_long_rides": len(long_rides),
        "avg_carbs_per_hour": round(sum(valid_cph) / len(valid_cph), 1) if valid_cph else 0,
        "avg_fueling_ratio": round(sum(valid_ratio) / len(valid_ratio), 2) if valid_ratio else None,
        "number_of_underfueled_sessions": underfueled,
    }


def print_report(activities: list, analyses: list, summary: dict) -> None:
    print("=" * 40)
    print("=== Fueling Analysis ===")
    print("=" * 40)
    print()
    print("Per Activity:")
    print()

    for activity, analysis in zip(activities, analyses):
        print(f"{analysis['date']} | {analysis['name']}")
        print(f"  Duration:        {analysis['duration_hours']:.1f} h")
        print(f"  Fueling Status:  {analysis['fueling_status']}")
        print(f"  Carbs/h:         {analysis['carbs_per_hour']:.0f} g  ({analysis['carbs_classification']})")
        if analysis["fueling_ratio"] is not None:
            print(f"  Fueling ratio:   {analysis['fueling_ratio']:.2f}  ({analysis['ratio_classification']})")
        else:
            print(f"  Fueling ratio:   n/a  (no carbs_used data)")
        if analysis["flags"]:
            print(f"  Flags:           {', '.join(analysis['flags'])}")
        print()

    print("-" * 40)
    print("Weekly Summary (long rides > 2 h):")
    print(f"  Long rides:           {summary['number_of_long_rides']}")
    print(f"  Avg carbs/h:          {summary['avg_carbs_per_hour']:.0f} g")
    if summary["avg_fueling_ratio"] is not None:
        print(f"  Avg fueling ratio:    {summary['avg_fueling_ratio']:.2f}")
    print(f"  Underfueled sessions: {summary['number_of_underfueled_sessions']}")
    print()

    print("-" * 40)
    print("Coaching Recommendations:")
    for rec in _build_recommendations(analyses, summary):
        print(f"  * {rec}")
    print()


def _build_recommendations(analyses: list, summary: dict) -> list:
    recommendations = []
    has_short_only = summary["number_of_long_rides"] == 0

    if has_short_only:
        recommendations.append("Short rides do not require fueling — focus on long sessions.")
    else:
        if summary["number_of_underfueled_sessions"] > 0:
            recommendations.append("Increase fueling on long rides — target at least 60 g/h.")
        if any("underfueled long ride" in a["flags"] for a in analyses):
            recommendations.append("Target 80–90 g/h on long rides (> 2 h).")
        if any("decoupling likely caused by low fueling" in a["flags"] for a in analyses):
            recommendations.append("Fueling likely limiting aerobic durability — address carbohydrate intake on longer sessions.")
        short_rides = [a for a in analyses if a["duration_hours"] < 1.5]
        if short_rides:
            recommendations.append("Short rides do not require fueling — focus on long sessions.")
        if not recommendations:
            recommendations.append("Fueling looks on track for this week.")
    return recommendations


def save_json(analyses: list, summary: dict, recommendations: list) -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    output_file = DATA_DIR / f"fueling_analysis_{monday.isoformat()}.json"
    output = {
        "week_starting": monday.isoformat(),
        "current_date": today.isoformat(),
        "activities": analyses,
        "weekly_summary": summary,
        "recommendations": recommendations,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(output, indent=2))
    print(f"Saved to: {output_file.name}")


def main() -> None:
    activities = load_data()
    if not activities:
        print("No activities found.")
        sys.exit(0)

    analyses = [analyze_activity(a) for a in activities]
    summary = summarize_week(analyses)
    recommendations = _build_recommendations(analyses, summary)
    print_report(activities, analyses, summary)
    save_json(analyses, summary, recommendations)


if __name__ == "__main__":
    main()
