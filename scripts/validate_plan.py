"""Validate a training plan JSON file against the upload schema.

Usage:
    python scripts/validate_plan.py
    python scripts/validate_plan.py --plan data/plans/my_plan.json
    python scripts/validate_plan.py --max-errors 20
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator
from check_plan_tss import RIDE_ACTIVITY_TYPES, planned_hours

DEFAULT_PLAN = Path(__file__).resolve().parents[1] / "data" / "plans" / "week_plan.json"
DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "contracts" / "week-plan" / "week-plan.schema.json"


def _path_for_error(parts: list[object]) -> str:
    if not parts:
        return "$"
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _message_for_error(error: object) -> str:
    validator = getattr(error, "validator", None)
    if validator == "oneOf":
        return "must match one of the allowed plan formats"
    if validator == "type":
        expected = getattr(error, "validator_value", "the expected type")
        return f"must be of type {expected}"
    if validator == "required":
        instance = getattr(error, "instance", None)
        required = getattr(error, "validator_value", [])
        if isinstance(instance, dict):
            missing = [name for name in required if name not in instance]
            if missing:
                return f"missing required property '{missing[0]}'"
        return "is missing a required property"
    if validator == "enum":
        return "must use an allowed value"
    if validator in ("contains", "minContains", "maxContains"):
        return "must contain exactly one canonical strength phase tag (strength-adaptation, strength-transition, strength-maximum, or strength-maintenance)"
    if validator == "maxItems":
        limit = getattr(error, "validator_value", None)
        return "must be absent or empty" if limit == 0 else f"must contain at most {limit} items"
    if validator in ("minimum", "maximum"):
        limit = getattr(error, "validator_value", None)
        return f"must be {'at least' if validator == 'minimum' else 'at most'} {limit}"
    if validator is None and getattr(error, "schema", None) is False:
        return "library_workout_id is not allowed for WeightTraining"
    if validator:
        return f"violates the '{validator}' schema rule"
    return "does not conform to the schema"


def _expand_schema_errors(errors: list[object]) -> list[object]:
    expanded: list[object] = []
    for error in errors:
        if getattr(error, "validator", None) == "oneOf" and getattr(error, "context", None):
            nested = _expand_schema_errors(list(error.context))
            specific = [nested_error for nested_error in nested if nested_error.absolute_path]
            expanded.extend(specific or nested)
        else:
            expanded.append(error)
    return expanded


def validate_plan_semantics(plan: list | dict, athlete_data: dict | None = None) -> list[str]:
    """Check date-level rules after schema validation; constraints are optional."""
    workouts = plan if isinstance(plan, list) else plan["workouts"]
    summary = (athlete_data or {}).get("week_summary") or {}
    if not isinstance(summary, dict):
        raise ValueError("athlete_data.week_summary must be an object")
    weeks = summary.get("training_plan") or []
    if not isinstance(weeks, list):
        raise ValueError("athlete_data.week_summary.training_plan must be an array")
    constraints = []
    for week in weeks:
        if not isinstance(week, dict):
            raise ValueError("athlete_data.week_summary.training_plan entries must be objects")
        days = week.get("day_constraints") or []
        if not isinstance(days, list) or any(not isinstance(day, dict) for day in days):
            raise ValueError("day_constraints must be an array of objects")
        constraints.extend(days)
    unavailable = {
        constraint["date"][:10] for constraint in constraints
        if constraint.get("training_allowed") is False and isinstance(constraint.get("date"), str)
    }
    seen: set[tuple[str, str]] = set()
    issues = []
    prefix = "$" if isinstance(plan, list) else "$.workouts"
    minutes_by_date: dict[str, float] = {}
    for workout in workouts:
        day = workout["date"][:10]
        minutes_by_date[day] = minutes_by_date.get(day, 0) + workout["duration_minutes"]
    for index, workout in enumerate(workouts):
        day = workout["date"][:10]
        activity_type = workout.get("activity_type") or "Ride"
        location = f"{prefix}[{index}]"
        category = "Ride" if activity_type in RIDE_ACTIVITY_TYPES else activity_type
        if category in ("Ride", "WeightTraining"):
            key = (day, category)
            if key in seen:
                issues.append(f"{location}.date: at most one {category} entry is allowed per calendar date ({day})")
            seen.add(key)
        if day in unavailable:
            issues.append(f"{location}.date: training is not allowed on {day}")
    for constraint in constraints:
        if constraint.get("type") != "LIMITED" or constraint.get("max_training_time_hours") is None:
            continue
        day = constraint.get("date")
        if not isinstance(day, str):
            raise ValueError("LIMITED day constraints require a date")
        day = day[:10]
        limit = float(constraint["max_training_time_hours"])
        total_hours = minutes_by_date.get(day, 0) / 60
        if total_hours > limit:
            issues.append(f"{prefix}: total planned duration on {day} is {total_hours:g} hours, exceeding the LIMITED-day budget of {limit:g} hours (all sports)")
    for week in weeks:
        target = week.get("weekly_time_target_hours")
        if target is None:
            continue
        if not isinstance(week.get("week"), str):
            raise ValueError("Training-plan weekly time targets require an ISO week date")
        week_start = date.fromisoformat(week["week"])
        week_end = week_start + timedelta(days=7)
        week_workouts = [
            workout for workout in workouts
            if week_start <= date.fromisoformat(workout["date"][:10]) < week_end
        ]
        ride_hours = planned_hours(week_workouts)["planned_ride_hours"]
        if ride_hours > float(target):
            issues.append(f"{prefix}: planned Ride duration for week {week_start} is {ride_hours:g} hours, exceeding weekly_time_target_hours {float(target):g}")
    return issues


def _load_json(path: Path, label: str) -> object:
    if not path.exists():
        print(f"Error: {label} file not found: {path}")
        sys.exit(1)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in {label} file {path}: {exc.msg} (line {exc.lineno}, column {exc.colno})")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a training plan JSON file against the upload schema.")
    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
        help="Path to plan JSON (default: data/plans/week_plan.json)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to JSON Schema (default: contracts/week-plan/week-plan.schema.json)",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=10,
        help="Maximum number of validation errors to print (default: 10)",
    )
    args = parser.parse_args()

    schema = _load_json(args.schema, "schema")
    plan = _load_json(args.plan, "plan")

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        print(f"Error: Invalid schema at {args.schema}: {exc}")
        sys.exit(1)

    validator = Draft202012Validator(schema)
    errors = sorted(
        _expand_schema_errors(list(validator.iter_errors(plan))),
        key=lambda err: list(err.absolute_path),
    )

    if not errors:
        print(f"Valid: {args.plan} conforms to {args.schema}")
        return

    max_errors = max(args.max_errors, 1)
    print(f"Invalid: found {len(errors)} validation error(s) in plan")
    for index, err in enumerate(errors[:max_errors], start=1):
        location = _path_for_error(list(err.absolute_path))
        print(f"  {index}. {location}: {_message_for_error(err)}")

    if len(errors) > max_errors:
        remaining = len(errors) - max_errors
        print(f"  ... and {remaining} more error(s)")

    sys.exit(1)


if __name__ == "__main__":
    main()
