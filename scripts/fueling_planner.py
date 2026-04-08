"""Generate carbohydrate intake recommendations for planned cycling activities.

Reads fueling_analysis activities (which include ride_type) from the consolidated
coach_input_{monday}.json and produces a per-session fueling plan with targets,
totals, and practical strategies.

Usage:
    python scripts/fueling_planner.py

Output:
    Console: per-session fueling plan
    File:    data/processed/fueling_plan_{monday}.json
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

# Target range (min, max) in g/h per ride type
_TARGETS: dict[str, tuple[int, int]] = {
    "vo2":                   (40, 60),
    "threshold":             (50, 70),
    "long_ride":             (80, 90),
    "endurance_long":        (60, 80),   # endurance >= 2 h
    "endurance_short":       (30, 50),   # endurance < 2 h (optional)
    "endurance_with_sprint": (40, 60),
    "recovery":              (0,  30),
}

_FATIGUE_BONUS = 10        # g/h added when form_pct < -0.20
_GEL_CARBS = 22            # g per gel (typical mid-range)
_BOTTLE_CARBS_SPORTS = 40  # g per 500 ml sports drink (standard mix)
_BOTTLE_CARBS_CONC = 60    # g per 500 ml concentrated sports drink


def _fueling_required(duration_hours: float) -> bool | str:
    """Return whether fueling is needed for the given duration."""
    if duration_hours < 1.5:
        return False
    if duration_hours < 2.0:
        return "optional"
    return True


def _target_range(ride_type: str, duration_hours: float) -> tuple[int, int]:
    """Return (min, max) g/h target for the ride type and duration."""
    if ride_type == "endurance":
        key = "endurance_long" if duration_hours >= 2.0 else "endurance_short"
    elif ride_type in _TARGETS:
        key = ride_type
    else:
        key = "endurance_long"
    return _TARGETS[key]


def _suggested_strategy(target_carbs_per_hour: int, duration_hours: float) -> list[str]:
    """Return practical fueling suggestions for the given target."""
    total = round(target_carbs_per_hour * duration_hours)

    if target_carbs_per_hour == 0:
        return ["No fueling needed"]

    if target_carbs_per_hour <= 30:
        return [
            "Water or light electrolytes only",
            f"Carbs optional — max {total} g if desired",
        ]

    if target_carbs_per_hour <= 50:
        return [
            f"1 energy gel every 45 min (~{_GEL_CARBS} g each)",
            f"Total: {total} g carbs",
        ]

    if target_carbs_per_hour <= 70:
        return [
            f"1 sports drink bottle per hour (~{_BOTTLE_CARBS_SPORTS} g)",
            f"1 energy gel every 30 min (~{_GEL_CARBS} g)",
            f"Total: {total} g carbs",
        ]

    # >= 70 g/h (long ride / high-intensity high-duration)
    suggestions = [
        f"1 concentrated sports drink bottle per hour (~{_BOTTLE_CARBS_CONC} g)",
        f"1 energy gel every 30 min (~{_GEL_CARBS} g)",
        f"Total: {total} g carbs",
    ]
    if duration_hours >= 2.5:
        suggestions.insert(2, "Consider solid food (rice cake or bar) every ~1.5 h (~40 g)")
    return suggestions


def plan_activity(activity: dict, form_pct: float | None = None) -> dict:
    """Build a fueling plan for a single activity.

    Args:
        activity: dict with at least ``duration_hours`` and ``ride_type``.
        form_pct: current Form % (CTL - ATL) / CTL.  When < -0.20 an extra
                  +10 g/h is applied to account for elevated carbohydrate demand
                  under high fatigue.

    Returns:
        dict with fueling targets, range, total carbs, and practical strategy.
    """
    duration = activity.get("duration_hours") or 0.0
    ride_type = activity.get("ride_type") or "endurance"
    name = activity.get("name") or "Unnamed ride"
    activity_date = activity.get("date") or ""

    required = _fueling_required(duration)

    if not required:
        return {
            "date": activity_date,
            "name": name,
            "duration_hours": round(duration, 2),
            "ride_type": ride_type,
            "fueling_required": False,
            "target_carbs_per_hour": 0,
            "target_range": (0, 0),
            "total_carbs": 0,
            "fueling_strategy": ["No fueling needed — ride < 1.5 h"],
            "fatigue_adjustment": False,
        }

    lo, hi = _target_range(ride_type, duration)
    fatigue_adjusted = False
    if form_pct is not None and form_pct < -0.20:
        lo = min(lo + _FATIGUE_BONUS, 120)
        hi = min(hi + _FATIGUE_BONUS, 120)
        fatigue_adjusted = True

    target = (lo + hi) // 2
    total_carbs = round(target * duration)
    strategy = _suggested_strategy(target, duration)

    return {
        "date": activity_date,
        "name": name,
        "duration_hours": round(duration, 2),
        "ride_type": ride_type,
        "fueling_required": required,
        "target_carbs_per_hour": target,
        "target_range": (lo, hi),
        "total_carbs": total_carbs,
        "fueling_strategy": strategy,
        "fatigue_adjustment": fatigue_adjusted,
    }


def generate_weekly_fueling_plan(
    activities: list[dict],
    form_pct: float | None = None,
) -> list[dict]:
    """Return a fueling plan for every activity in the list."""
    return [plan_activity(a, form_pct) for a in activities]


def _day_label(activity_date: str) -> str:
    try:
        d = date.fromisoformat(activity_date)
        return d.strftime("%A")
    except ValueError:
        return activity_date


def print_plan(plan: list[dict]) -> None:
    """Print the fueling plan to stdout."""
    print("=== Fueling Plan ===\n")
    for p in plan:
        label = _day_label(p["date"])
        ride_type = p["ride_type"].replace("_", " ").title()
        print(f"{label}  —  {p['name']} ({ride_type})")
        print(f"  Duration:  {p['duration_hours']:.1f} h")
        if p["fueling_required"]:
            lo, hi = p["target_range"]
            print(f"  Target:    {p['target_carbs_per_hour']} g/h  ({lo}–{hi} g/h range)")
            print(f"  Total:     {p['total_carbs']} g carbs")
            if p["fatigue_adjustment"]:
                print(f"  Note:      +{_FATIGUE_BONUS} g/h fatigue adjustment applied (high training load)")
            print("  Suggested:")
            for line in p["fueling_strategy"]:
                print(f"    - {line}")
        else:
            print("  No fueling needed")
        print()


def save_json(plan: list[dict], monday: date) -> None:
    output_file = DATA_DIR / f"fueling_plan_{monday.isoformat()}.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    serializable = [
        {**p, "target_range": list(p["target_range"])} for p in plan
    ]
    output_file.write_text(json.dumps(serializable, indent=2))
    print(f"Saved to: {output_file.name}")


def main() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    input_file = DATA_DIR / f"coach_input_{monday.isoformat()}.json"
    if not input_file.exists():
        files = sorted(DATA_DIR.glob("coach_input_*.json"))
        if not files:
            print("Error: No coach_input JSON file found in data/processed/.")
            sys.exit(1)
        input_file = files[-1]

    print(f"Loading {input_file.name}\n")
    data = json.loads(input_file.read_text())

    # fueling_analysis.activities already carry ride_type from fueling_analysis.py
    activities = data.get("fueling_analysis", {}).get("activities", [])
    if not activities:
        # Fall back to main activities list (ride_type will default to endurance)
        activities = data.get("activities", [])

    form_pct = data.get("week_summary", {}).get("form_pct")

    plan = generate_weekly_fueling_plan(activities, form_pct)
    print_plan(plan)
    save_json(plan, monday)


if __name__ == "__main__":
    main()
