"""Read the latest training_plan JSON and produce a simplified planned-workouts JSON for coach analysis.

Reads data/processed/training_plan_{today}.json (or the most recent available file),
extracts all planned workouts for the current and next ISO week, and saves a
simplified representation to data/processed/planned_workouts_{monday}.json.

Usage:
    python scripts/prepare_planned_workouts_for_coach.py
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_training_plan() -> dict | None:
    """Return the most recent training_plan_*.json content, or None if not found."""
    files = sorted(PROCESSED_DIR.glob("training_plan_*.json"))
    if not files:
        print("No training_plan_*.json found in data/processed/. Run get_training_plan.py first.")
        return None
    latest = files[-1]
    print(f"Loading {latest.name}")
    return json.loads(latest.read_text(encoding="utf-8"))


def _parse_steps(workout_doc: dict | None) -> list[dict] | None:
    """Return a simplified list of workout steps from the workout_doc structure."""
    if not workout_doc:
        return None
    raw_steps = workout_doc.get("steps") or []
    result = []
    for step in raw_steps:
        duration_s = step.get("duration") or 0
        power_info = step.get("power") or {}
        power_value = power_info.get("value")
        power_units = power_info.get("units", "%ftp")
        result.append({
            "duration_min": round(duration_s / 60, 1),
            "power_pct_ftp": power_value if power_units == "%ftp" else None,
            "power_watts": power_value if power_units == "watts" else None,
        })
    return result if result else None


def _simplify_workout(ev: dict) -> dict:
    """Extract the coach-relevant fields from a raw workout event."""
    start = ev.get("start_date_local", "")
    duration_s = ev.get("moving_time") or 0

    workout_doc = ev.get("workout_doc")
    zone_times = (workout_doc or {}).get("zoneTimes") or []
    secs_by_id = {z["id"]: z["secs"] for z in zone_times if "id" in z and "secs" in z}
    total_secs = sum(secs_by_id.values())
    if total_secs > 0:
        z1_z2 = secs_by_id.get("Z1", 0) + secs_by_id.get("Z2", 0)
        z3_z4 = secs_by_id.get("Z3", 0) + secs_by_id.get("Z4", 0)
        z5_plus = sum(v for k, v in secs_by_id.items() if k in ("Z5", "Z6", "Z7"))
        zone_distribution = {
            "z1_z2_pct": round(z1_z2 / total_secs * 100, 1),
            "z3_z4_pct": round(z3_z4 / total_secs * 100, 1),
            "z5_plus_pct": round(z5_plus / total_secs * 100, 1),
        }
    else:
        zone_distribution = None

    return {
        "date": start[:10],
        "time": start[11:16] if len(start) > 10 else None,
        "name": ev.get("name") or "(unnamed)",
        "type": ev.get("type"),
        "duration_hours": round(duration_s / 3600, 2) if duration_s else None,
        "planned_load": ev.get("icu_training_load"),
        "description": ev.get("description"),
        "zone_distribution": zone_distribution,
        "steps": _parse_steps(workout_doc),
    }


def filter_workouts_for_week(workouts: list[dict], week_monday: date) -> list[dict]:
    """Return workouts whose date falls within the ISO week starting on week_monday."""
    week_start = week_monday.isoformat()
    week_end = (week_monday + timedelta(days=6)).isoformat()
    return [w for w in workouts if week_start <= (w.get("start_date_local") or "")[:10] <= week_end]


def main() -> None:
    plan = load_training_plan()
    if plan is None:
        sys.exit(1)

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(weeks=1)

    raw_workouts: list[dict] = plan.get("workouts") or []

    current_week_workouts = [_simplify_workout(w) for w in filter_workouts_for_week(raw_workouts, monday)]
    next_week_workouts = [_simplify_workout(w) for w in filter_workouts_for_week(raw_workouts, next_monday)]

    output = {
        "generated_on": today.isoformat(),
        "current_week": {
            "week_starting": monday.isoformat(),
            "planned_workouts": current_week_workouts,
        },
        "next_week": {
            "week_starting": next_monday.isoformat(),
            "planned_workouts": next_week_workouts,
        },
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / f"planned_workouts_{monday.isoformat()}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved -> {output_path}")

    total = len(current_week_workouts) + len(next_week_workouts)
    print(f"  Current week ({monday}): {len(current_week_workouts)} workouts")
    print(f"  Next week    ({next_monday}): {len(next_week_workouts)} workouts")
    print(f"  Total: {total} workouts")


if __name__ == "__main__":
    main()
