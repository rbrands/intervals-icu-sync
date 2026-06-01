"""List workouts that are shared by a specific athlete.

This script traverses the folder/plan tree from intervals.icu and extracts
workouts only from folders/plans that are shared by the selected athlete.

Usage:
    python scripts/list_shared_workouts.py
    python scripts/list_shared_workouts.py --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.client import get_library_folders
from intervals_icu.config import API_KEY, ATHLETE_ID


def _format_duration(seconds: int | float | None) -> str:
    total_seconds = int(seconds or 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _is_shared_folder(folder: dict) -> bool:
    # Outgoing sharing: PUBLIC folders/plans or explicitly shared ones.
    visibility = (folder.get("visibility") or "").upper()
    shared_with_count = int(folder.get("sharedWithCount") or 0)
    has_share_token = bool(folder.get("shareToken"))
    return visibility == "PUBLIC" or shared_with_count > 0 or has_share_token


def _owner_label(folder: dict, fallback_athlete_id: str) -> str:
    owner = folder.get("owner")
    if isinstance(owner, dict):
        return owner.get("name") or owner.get("id") or fallback_athlete_id
    return fallback_athlete_id


def _collect_shared_workouts(
    nodes: list,
    athlete_id: str,
    parent_path: str = "",
    shared_context: dict | None = None,
) -> list[dict]:
    results: list[dict] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")
        if node_type in {"FOLDER", "PLAN"}:
            name = node.get("name") or f"Folder {node.get('id')}"
            path = f"{parent_path} / {name}" if parent_path else name

            current_shared = shared_context
            if _is_shared_folder(node):
                current_shared = {
                    "shared_from": _owner_label(node, athlete_id),
                    "folder_path": path,
                    "folder_id": node.get("id"),
                }

            children = node.get("children") or []
            results.extend(_collect_shared_workouts(children, athlete_id, path, current_shared))
            continue

        # Workout leaf node
        if shared_context and node.get("id") is not None:
            results.append(
                {
                    "shared_from": shared_context["shared_from"],
                    "folder": shared_context["folder_path"],
                    "name": node.get("name") or "(unnamed)",
                    "duration": _format_duration(node.get("moving_time")),
                    "duration_seconds": int(node.get("moving_time") or 0),
                    "tss": node.get("icu_training_load") or 0,
                    "tags": node.get("tags") or [],
                }
            )

    return results


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No shared workouts found for this athlete.")
        return

    headers = {
        "shared_from": "Shared From",
        "folder": "Folder",
        "name": "Workout",
        "duration": "Duration",
        "tss": "TSS",
        "tags": "Tags",
    }

    display_rows = [
        {
            "shared_from": row["shared_from"],
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
        description="List workouts shared by the selected athlete."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print normalized shared workout data as JSON.",
    )
    parser.add_argument(
        "--athlete-id",
        default=ATHLETE_ID,
        help="Athlete id whose shared library should be listed (defaults to ATHLETE_ID from .env).",
    )
    args = parser.parse_args()

    folders = get_library_folders(API_KEY, args.athlete_id)
    shared_workouts = _collect_shared_workouts(folders, args.athlete_id)
    shared_workouts.sort(key=lambda r: (r["shared_from"], r["folder"], r["name"].lower()))

    if args.json:
        print(json.dumps(shared_workouts, indent=2, ensure_ascii=False))
        return

    _print_table(shared_workouts)
    print(f"\nTotal shared workouts: {len(shared_workouts)}")


if __name__ == "__main__":
    main()