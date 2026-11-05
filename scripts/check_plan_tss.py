"""Check a generated weekly plan against a deterministic TSS reference.

Reads a JSON file containing a weekly plan, reports each workout's stated TSS
next to the step-based computed TSS, then checks Ride-only weekly load (using
the computed values) against a Ride target. Non-ride entries are listed but
excluded from the target. Per-workout mismatches are informational; only the
weekly target deviation and the optional Ride time budget make a plan invalid.

Usage:
    python scripts/check_plan_tss.py --plan /tmp/plan.json --load-target 300 --tolerance-pct 10
    python scripts/check_plan_tss.py --plan data/plans/my_plan.json --load-target 300
"""

import argparse
import json
import re
import sys
from pathlib import Path

RIDE_ACTIVITY_TYPES = {"Ride", "VirtualRide", "MountainBikeRide", "GravelRide"}


def planned_hours(plan: list[dict]) -> dict[str, float]:
    """Split planned duration using the same sport scope as Ride TSS."""
    ride_minutes = 0.0
    other_minutes = 0.0
    for workout in plan:
        if not isinstance(workout, dict):
            continue
        minutes = float(workout.get("duration_minutes") or 0)
        activity_type = workout.get("activity_type")
        if activity_type is None or activity_type in RIDE_ACTIVITY_TYPES:
            ride_minutes += minutes
        else:
            other_minutes += minutes
    return {
        "planned_ride_hours": ride_minutes / 60,
        "planned_other_hours": other_minutes / 60,
    }


def _step_values(step: dict) -> tuple[float, float]:
    """Return (duration_seconds, power_pct_ftp), accepting the legacy aliases."""
    duration_seconds = float(step.get("duration_seconds") or step.get("duration") or 0)
    power_pct_ftp = float(step.get("power_pct_ftp") or step.get("power") or 0)
    return max(duration_seconds, 0.0), power_pct_ftp


def _compute_tss_from_steps(steps: list[dict]) -> int:
    total = 0.0
    for step in steps:
        if not isinstance(step, dict):
            continue
        duration_seconds, power_pct_ftp = _step_values(step)
        total += (duration_seconds / 3600) * (power_pct_ftp / 100) ** 2 * 100
    return round(total)


def _compute_duration_minutes_from_steps(steps: list[dict]) -> float | int:
    total_seconds = sum(_step_values(step)[0] for step in steps if isinstance(step, dict))
    minutes = total_seconds / 60
    return int(minutes) if minutes.is_integer() else round(minutes, 2)


def _workout_steps(workout: dict) -> list[dict]:
    document = workout.get("workout")
    steps = document.get("steps") if isinstance(document, dict) else workout.get("steps")
    return steps if isinstance(steps, list) else []


def _is_ride(workout: dict) -> bool:
    activity_type = workout.get("activity_type")
    return activity_type is None or activity_type in RIDE_ACTIVITY_TYPES


_TSS_MENTION = re.compile(r"\bTSS:\s*~?\d+(?:\.\d+)?")


def _replace_tss_mention(description, tss: int):
    if not isinstance(description, str):
        return description
    return _TSS_MENTION.sub(f"TSS: {tss}", description)


def normalize_workout_load(workout: dict) -> dict:
    """Return a copy with step-derived tss/duration for generated rides.

    Generated rides with steps get tss, the "TSS: <n>" description mention,
    and duration_minutes recomputed from the steps. WeightTraining gets tss 0.
    Library workouts and other entries are returned unchanged.
    """
    if not isinstance(workout, dict) or workout.get("library_workout_id") is not None:
        return workout
    if workout.get("activity_type") == "WeightTraining":
        normalized = dict(workout)
        normalized["tss"] = 0
        if "description" in normalized:
            normalized["description"] = _replace_tss_mention(normalized["description"], 0)
        return normalized
    steps = _workout_steps(workout)
    if not _is_ride(workout) or not steps:
        return workout
    tss = _compute_tss_from_steps(steps)
    normalized = dict(workout)
    normalized["tss"] = tss
    normalized["duration_minutes"] = _compute_duration_minutes_from_steps(steps)
    if "description" in normalized:
        normalized["description"] = _replace_tss_mention(normalized["description"], tss)
    return normalized


def _normalize_plan(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("workouts"), list):
        return data["workouts"]
    raise ValueError("Plan file must contain a JSON array or an object with a 'workouts' array.")


def evaluate_plan(
    plan: list[dict],
    load_target: float | None = None,
    tolerance_pct: float = 10.0,
    completed_tss: float = 0.0,
    weekly_time_target_hours: float | None = None,
) -> dict:
    """Compare planned and completed Ride TSS with a Ride target.

    Per-workout stated vs step-based TSS is reported, but only the weekly
    target deviation (and the optional Ride time budget) affects validity.
    """
    warnings: list[str] = []
    notes: list[str] = []
    workout_results: list[dict] = []
    planned_tss = 0
    planned_other_tss = 0
    normalized_plan: list[dict] = []

    for workout in plan:
        if not isinstance(workout, dict):
            continue

        date = workout.get("date", "unknown")
        stated_tss = workout.get("tss")
        if stated_tss is None:
            stated_tss = 0
        stated_tss = int(stated_tss)

        normalized = normalize_workout_load(workout)
        normalized_plan.append(normalized)
        counted = _is_ride(workout)
        computed_tss = int(normalized.get("tss") or 0) if normalized is not workout else stated_tss
        mismatch = computed_tss != stated_tss
        if mismatch:
            notes.append(
                f"Workout on {date}: stated_tss {stated_tss} differs from computed_tss {computed_tss}; "
                "the computed value is used for the weekly total and overwritten on upload."
            )

        workout_results.append(
            {
                "date": date,
                "stated_tss": stated_tss,
                "computed_tss": computed_tss,
                "mismatch": mismatch,
                "counted": counted,
            }
        )
        if counted:
            planned_tss += computed_tss
        else:
            planned_other_tss += computed_tss

    completed_tss = float(completed_tss)
    total_tss = planned_tss + completed_tss
    load_target = float(load_target) if load_target is not None else None
    if load_target in (None, 0):
        deviation_pct = 0.0
        within_tolerance = True
    else:
        deviation_pct = ((total_tss - load_target) / load_target) * 100
        within_tolerance = abs(deviation_pct) <= float(tolerance_pct)
        if not within_tolerance:
            direction = "below" if deviation_pct < 0 else "above"
            guidance = (
                "Add or extend low/moderate sessions on available days to close the gap"
                if deviation_pct < 0
                else "Reduce duration or intensity before finalizing"
            )
            warnings.append(
                f"Weekly total {total_tss:g} TSS is {abs(deviation_pct):.1f}% {direction} the target of {int(load_target)} TSS (tolerance ±{tolerance_pct}%). {guidance}; do not modify anchored planned_workouts."
            )

    hours = planned_hours(normalized_plan)
    time_within_budget = (
        weekly_time_target_hours is None
        or hours["planned_ride_hours"] <= float(weekly_time_target_hours)
    )
    if not time_within_budget:
        warnings.append(
            f"Planned Ride duration {hours['planned_ride_hours']:g} hours exceeds the weekly Ride time budget of {weekly_time_target_hours:g} hours."
        )
    valid = within_tolerance and time_within_budget
    return {
        "workouts": workout_results,
        "week": {
            **hours,
            "weekly_time_target_hours": weekly_time_target_hours,
            "time_within_budget": time_within_budget,
            "completed_tss": completed_tss,
            "planned_tss": planned_tss,
            "planned_ride_tss": planned_tss,
            "planned_other_tss": planned_other_tss,
            "total_tss": total_tss,
            "load_target": load_target if load_target is not None else 0,
            "deviation_pct": deviation_pct,
            "within_tolerance": within_tolerance,
        },
        "valid": valid,
        "issues": warnings,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Ride TSS against a Ride target; non-ride entries are listed but excluded.")
    parser.add_argument("--plan", type=Path, required=True, help="Path to the plan JSON file.")
    parser.add_argument("--load-target", type=float, default=None, help="Weekly Ride TSS target; non-ride entries are excluded.")
    parser.add_argument("--tolerance-pct", type=float, default=10.0, help="Allowed weekly deviation as a percentage.")
    parser.add_argument("--weekly-time-target-hours", type=float, default=None, help="Optional upper budget for planned Ride hours; non-ride duration is excluded.")
    parser.add_argument(
        "--completed-tss",
        type=float,
        default=0.0,
        help="Ride TSS already completed this week; added to planned Ride TSS against the full weekly Ride target.",
    )
    args = parser.parse_args()

    try:
        if not args.plan.exists():
            raise FileNotFoundError(f"Plan file not found: {args.plan}")
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        workouts = _normalize_plan(data)
        result = evaluate_plan(
            workouts,
            load_target=args.load_target,
            tolerance_pct=args.tolerance_pct,
            completed_tss=args.completed_tss,
            weekly_time_target_hours=args.weekly_time_target_hours,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "workouts": [],
            "week": {
                "planned_ride_hours": 0,
                "planned_other_hours": 0,
                "weekly_time_target_hours": args.weekly_time_target_hours,
                "time_within_budget": True,
                "completed_tss": float(args.completed_tss),
                "planned_tss": 0,
                "planned_ride_tss": 0,
                "planned_other_tss": 0,
                "total_tss": float(args.completed_tss),
                "load_target": float(args.load_target) if args.load_target is not None else 0,
                "deviation_pct": 0,
                "within_tolerance": True,
            },
            "valid": False,
            "issues": [str(exc)],
            "notes": [],
        }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
