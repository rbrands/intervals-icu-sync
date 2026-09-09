"""Validate a training plan JSON file against the upload schema.

Usage:
    python scripts/validate_plan.py
    python scripts/validate_plan.py --plan data/plans/my_plan.json
    python scripts/validate_plan.py --max-errors 20
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

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
