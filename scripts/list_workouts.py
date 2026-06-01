"""List all workouts from the athlete's intervals.icu workout library.

Shows the key planning fields per workout: folder, duration, TSS, and tags.

Usage:
    python scripts/list_workouts.py
    python scripts/list_workouts.py --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.client import get_library_folders, get_library_workouts
from intervals_icu.config import API_KEY, ATHLETE_ID


def _flatten_folders(folders: list, parent_path: str = "") -> dict[int, str]:
    folder_map: dict[int, str] = {}
    for entry in folders:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") not in {"FOLDER", "PLAN"}:
            continue

        name = entry.get("name") or f"Folder {entry.get('id')}"
        path = f"{parent_path} / {name}" if parent_path else name
        folder_id = entry.get("id")
        if isinstance(folder_id, int):
            folder_map[folder_id] = path

        children = entry.get("children") or []
        folder_map.update(_flatten_folders(children, path))
    return folder_map


def _format_duration(seconds: int | float | None) -> str:
    total_seconds = int(seconds or 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _normalize_workout(workout: dict, folder_map: dict[int, str]) -> dict:
    tags = workout.get("tags") or []
    folder_name = folder_map.get(workout.get("folder_id"), "-")
    return {
        "folder": folder_name,
        "name": workout.get("name") or "(unnamed)",
        "duration": _format_duration(workout.get("moving_time")),
        "duration_seconds": int(workout.get("moving_time") or 0),
        "tss": workout.get("icu_training_load") or 0,
        "tags": tags,
    }


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No workouts found in the library.")
        return

    headers = {
        "folder": "Folder",
        "name": "Workout",
        "duration": "Duration",
        "tss": "TSS",
        "tags": "Tags",
    }
    display_rows = [
        {
            "folder": row["folder"],
            "name": row["name"],
            "duration": row["duration"],
            "tss": str(row["tss"]),
            "tags": ", ".join(row["tags"]) if row["tags"] else "-",
        }
        for row in rows
    ]

    widths = {
        key: max(len(headers[key]), max(len(item[key]) for item in display_rows))
        for key in headers
    }
    line = "  ".join(headers[key].ljust(widths[key]) for key in headers)
    separator = "  ".join("-" * widths[key] for key in headers)

    print(line)
    print(separator)
    for row in display_rows:
        print("  ".join(row[key].ljust(widths[key]) for key in headers))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List all workouts from the intervals.icu workout library."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print normalized workout data as JSON instead of a table.",
    )
    args = parser.parse_args()

    folders = get_library_folders(API_KEY, ATHLETE_ID)
    workouts = get_library_workouts(API_KEY, ATHLETE_ID)
    folder_map = _flatten_folders(folders)

    normalized = sorted(
        (_normalize_workout(workout, folder_map) for workout in workouts),
        key=lambda row: (row["folder"], row["name"].lower()),
    )

    if args.json:
        print(json.dumps(normalized, indent=2, ensure_ascii=False))
        return

    _print_table(normalized)
    print(f"\nTotal workouts: {len(normalized)}")


if __name__ == "__main__":
    main()