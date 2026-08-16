"""Check a generated weekly plan against a deterministic TSS reference.

Reads a JSON file containing a weekly plan and verifies each workout's TSS value
against the sum of step-based TSS values, then checks total weekly load against
an expected target.

Usage:
    python scripts/check_plan_tss.py --plan /tmp/plan.json --load-target 300 --tolerance-pct 10
    python scripts/check_plan_tss.py --plan data/plans/my_plan.json --load-target 300
"""

import argparse
import json
import sys
from pathlib import Path


def _compute_tss_from_steps(steps: list[dict]) -> int:
    total = 0.0
    for step in steps:
        duration_seconds = float(step.get("duration_seconds") or 0)
        power_pct_ftp = float(step.get("power_pct_ftp") or 0)
        total += (duration_seconds / 3600) * (power_pct_ftp / 100) ** 2 * 100
    return round(total)


def _normalize_plan(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("workouts"), list):
        return data["workouts"]
    raise ValueError("Plan file must contain a JSON array or an object with a 'workouts' array.")


def evaluate_plan(plan: list[dict], load_target: float | None = None, tolerance_pct: float = 10.0) -> dict:
    warnings: list[str] = []
    workout_results: list[dict] = []
    total_tss = 0

    for workout in plan:
        if not isinstance(workout, dict):
            continue

        date = workout.get("date", "unknown")
        stated_tss = workout.get("tss")
        if stated_tss is None:
            stated_tss = 0
        stated_tss = int(stated_tss)

        library_workout_id = workout.get("library_workout_id")
        steps = workout.get("steps") or []

        if library_workout_id is not None:
            computed_tss = stated_tss
            mismatch = False
            tolerance = 0
        elif isinstance(steps, list) and steps:
            computed_tss = _compute_tss_from_steps(steps)
            tolerance = max(2, round(0.05 * computed_tss))
            mismatch = abs(computed_tss - stated_tss) > tolerance
            if mismatch:
                warnings.append(
                    f"Workout on {date} (stated_tss {stated_tss}) does not match steps-based computed_tss {computed_tss} (diff {abs(computed_tss - stated_tss)}, tolerance ±{tolerance}). Recompute TSS from steps and correct the tss field and description."
                )
        else:
            computed_tss = stated_tss
            mismatch = False
            tolerance = 0

        workout_results.append(
            {
                "date": date,
                "stated_tss": stated_tss,
                "computed_tss": computed_tss,
                "mismatch": mismatch,
            }
        )
        total_tss += computed_tss

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
                f"Weekly total {total_tss} TSS is {abs(deviation_pct):.1f}% {direction} the target of {int(load_target)} TSS (tolerance ±{tolerance_pct}%). {guidance}; do not modify anchored planned_workouts."
            )

    valid = not any(workout["mismatch"] for workout in workout_results) and within_tolerance
    return {
        "workouts": workout_results,
        "week": {
            "total_tss": total_tss,
            "load_target": load_target if load_target is not None else 0,
            "deviation_pct": deviation_pct,
            "within_tolerance": within_tolerance,
        },
        "valid": valid,
        "issues": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check computed TSS values for a generated weekly plan.")
    parser.add_argument("--plan", type=Path, required=True, help="Path to the plan JSON file.")
    parser.add_argument("--load-target", type=float, default=None, help="Weekly TSS target for the plan.")
    parser.add_argument("--tolerance-pct", type=float, default=10.0, help="Allowed weekly deviation as a percentage.")
    args = parser.parse_args()

    try:
        if not args.plan.exists():
            raise FileNotFoundError(f"Plan file not found: {args.plan}")
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        workouts = _normalize_plan(data)
        result = evaluate_plan(workouts, load_target=args.load_target, tolerance_pct=args.tolerance_pct)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "workouts": [],
            "week": {
                "total_tss": 0,
                "load_target": float(args.load_target) if args.load_target is not None else 0,
                "deviation_pct": 0,
                "within_tolerance": True,
            },
            "valid": False,
            "issues": [str(exc)],
        }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
