"""Print a compact activity list in the same format as the MCP get_latest_activities tool.

Reads the most recent coach_input_{monday}.json from data/processed/ and returns
the same compact JSON structure that the webservice MCP tool would send to a client.

Usage:
    python scripts/get_latest_activities.py [--limit N]

Output is written to stdout as pretty-printed JSON.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

_DEFAULT_PROCESSED_DIR = _ROOT / "data" / "processed"
PROCESSED_DIR = Path(os.environ.get("INTERVALS_PROCESSED_DIR", str(_DEFAULT_PROCESSED_DIR)))

try:
    _version_file = _ROOT / "VERSION"
    SCHEMA_VERSION = _version_file.read_text(encoding="utf-8").strip() if _version_file.exists() else "unknown"
except Exception:
    SCHEMA_VERSION = "unknown"


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def load_activities(limit: int) -> dict:
    monday = _current_monday()
    input_file = PROCESSED_DIR / f"coach_input_{monday.isoformat()}.json"

    if not input_file.exists():
        files = sorted(PROCESSED_DIR.glob("coach_input_*.json"))
        if not files:
            return {"error": "No coach_input file found. Run prepare_week_for_coach.py first."}
        input_file = files[-1]

    data = json.loads(input_file.read_text(encoding="utf-8"))

    activities = (
        data if isinstance(data, list)
        else (data or {}).get("activities")
    )

    if not isinstance(activities, list):
        return {"error": "No activities found in coach_input file."}

    activities_sorted = sorted(
        activities,
        key=lambda a: (a.get("date") or "", a.get("name") or ""),
        reverse=True,
    )

    compact = [
        {
            "date": a.get("date"),
            "name": a.get("name"),
            "duration_hours": a.get("duration_hours"),
            "training_load": a.get("training_load"),
            "avg_hr": a.get("avg_hr"),
            "max_hr": a.get("max_hr"),
            "rpe": a.get("rpe"),
            "tags": a.get("tags") or [],
        }
        for a in activities_sorted[:limit]
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "week_starting": monday.isoformat(),
        "current_date": date.today().isoformat(),
        "source_file": input_file.name,
        "total_activities": len(activities),
        "returned": len(compact),
        "activities": compact,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print compact activity list — same format as MCP get_latest_activities."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of activities to return (default: 10).",
    )
    args = parser.parse_args()

    if not (1 <= args.limit <= 100):
        print("Error: --limit must be between 1 and 100.", file=sys.stderr)
        sys.exit(1)

    result = load_activities(args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
