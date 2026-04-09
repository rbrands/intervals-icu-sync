"""Upload a JSON training plan to intervals.icu as planned workouts.

Reads data/plans/week_plan.json (or a path passed via --plan) and creates
one planned activity per entry using the intervals.icu API.

Each entry in the JSON file must have:
    date            – ISO 8601 datetime string, e.g. "2026-04-12T09:00:00"
    name            – display name of the workout
    duration_minutes – planned duration in minutes (integer or float)

Optional per entry:
    description     – free-text notes added to the activity

Usage:
    python scripts/upload_plan.py
    python scripts/upload_plan.py --plan data/plans/my_plan.json
    python scripts/upload_plan.py --dry-run
"""

import argparse
import base64
import json
import json as _json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Activate .venv if running outside of it (adds site-packages to sys.path)
_venv_site = Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"
if _venv_site.exists() and str(_venv_site) not in sys.path:
    sys.path.insert(0, str(_venv_site))

import requests
from intervals_icu.client import _ascii_safe, _steps_to_zwo, create_activity, delete_events_range, get_events, update_event
from intervals_icu.config import API_KEY, ATHLETE_ID

DEFAULT_PLAN = Path(__file__).resolve().parents[1] / "data" / "plans" / "week_plan.json"


def load_plan(path: Path) -> list[dict]:
    if not path.exists():
        print(f"Error: Plan file not found: {path}")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    # Support both a bare array and {"week": ..., "workouts": [...]}
    if isinstance(data, list):
        return data, ""
    if isinstance(data, dict) and "workouts" in data:
        week = data.get("week", "")
        if week:
            print(f"Week: {week}")
        workouts = data["workouts"]
        if isinstance(workouts, list):
            return workouts, week
    print("Error: Plan file must contain a JSON array or an object with a 'workouts' array.")
    sys.exit(1)


def _validate_workout(workout: dict, index: int) -> bool:
    missing = [f for f in ("date", "name", "duration_minutes") if not workout.get(f)]
    if missing:
        print(f"  Skipping entry {index + 1}: missing required fields: {', '.join(missing)}")
        return False
    return True


def upload_plan(plan: list[dict], week: str = "", dry_run: bool = False, clear: bool = False) -> None:
    success = 0
    skipped = 0
    failed = 0

    dates = [w["date"][:10] for w in plan if w.get("date")]
    oldest = min(dates) if dates else None
    newest = max(dates) if dates else None

    if clear and not dry_run and oldest:
        print(f"Clearing WORKOUT events {oldest} – {newest} ...")
        try:
            delete_events_range(API_KEY, ATHLETE_ID, oldest, newest)
            print("  Done.\n")
        except requests.HTTPError as exc:
            print(f"  Failed to clear events — HTTP {exc.response.status_code}: {exc.response.text[:120]}")
            sys.exit(1)
        except requests.RequestException as exc:
            print(f"  Failed to clear events — {exc}")
            sys.exit(1)

    # Fetch existing WORKOUT events for the date range and index by (name, date).
    existing: dict[tuple[str, str], int] = {}
    if not dry_run and not clear and oldest:
        try:
            events = get_events(API_KEY, ATHLETE_ID, oldest, newest)
            for ev in events:
                key = (ev.get("name", ""), ev.get("start_date_local", "")[:10])
                existing[key] = ev["id"]
        except requests.RequestException:
            pass  # If fetch fails, fall back to always creating

    for i, workout in enumerate(plan):
        if not _validate_workout(workout, i):
            skipped += 1
            continue

        name = workout["name"]
        date = workout["date"]
        duration_seconds = int(float(workout["duration_minutes"]) * 60)
        description = workout.get("description", "")
        fueling = workout.get("fueling")
        if fueling:
            carbs_per_hour = fueling.get("carbs_per_hour")
            total_carbs = fueling.get("total_carbs")
            parts = []
            if carbs_per_hour is not None:
                parts.append(f"{carbs_per_hour}g carbs/h")
            if total_carbs is not None:
                parts.append(f"{total_carbs}g total")
            if parts:
                description = f"{description}\nFueling: {', '.join(parts)}" if description else f"Fueling: {', '.join(parts)}"
        workout_doc = workout.get("workout")

        if dry_run:
            steps = len(workout_doc["steps"]) if workout_doc else 0
            suffix = f", {steps} steps" if steps else ""
            print(f"  [dry-run] Would upload: {name} on {date[:10]}  ({duration_seconds // 60} min{suffix})")
            success += 1
            continue

        existing_id = existing.get((name, date[:10]))

        try:
            if existing_id:
                # Build same payload as create_activity and PUT to the existing event.
                payload = {
                    "name": name,
                    "start_date_local": date,
                    "type": "Ride",
                    "category": "WORKOUT",
                    "moving_time": duration_seconds,
                    "description": description,
                }
                if workout_doc is not None and "steps" in workout_doc:
                    zwo = _steps_to_zwo(name, _ascii_safe(description), workout_doc["steps"])
                    payload["file_contents_base64"] = base64.b64encode(zwo.encode()).decode()
                    payload["filename"] = "workout.zwo"
                result = update_event(API_KEY, ATHLETE_ID, existing_id, payload)
                print(f"  Updated:  {name} on {date[:10]}")
            else:
                result = create_activity(
                    api_key=API_KEY,
                    athlete_id=ATHLETE_ID,
                    name=name,
                    start_date_local=date,
                    duration=duration_seconds,
                    description=description,
                    workout=workout_doc,
                )
                print(f"  Created:  {name} on {date[:10]}")
            success += 1
        except requests.HTTPError as exc:
            print(f"  Failed:   {name} on {date[:10]} — HTTP {exc.response.status_code}: {exc.response.text[:120]}")
            failed += 1
        except requests.RequestException as exc:
            print(f"  Failed:   {name} on {date[:10]} — {exc}")
            failed += 1

    print()
    print(f"Done — {success} uploaded, {skipped} skipped, {failed} failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a JSON training plan to intervals.icu.")
    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
        help="Path to the JSON plan file (default: data/plans/week_plan.json)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all WORKOUT events for the plan's date range before uploading (use to fix duplicates).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be uploaded without making any API calls.",
    )
    args = parser.parse_args()

    print(f"Loading plan: {args.plan.name}")
    plan, week = load_plan(args.plan)
    print(f"Found {len(plan)} workout(s)\n")

    upload_plan(plan, week=week, dry_run=args.dry_run, clear=args.clear)


if __name__ == "__main__":
    main()
