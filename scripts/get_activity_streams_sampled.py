"""Fetch and print sampled activity streams for a single activity.

Usage:
    python scripts/get_activity_streams_sampled.py --id <activity_id>
    python scripts/get_activity_streams_sampled.py --id <activity_id> --streams time,distance,heartrate --max-points 250

The script mirrors the public MCP tool and follows the same local-script pattern
used elsewhere in this repository: environment variables via .env and JSON output
on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intervals_icu.client import get_activity_streams_sampled as fetch_sampled_streams
from intervals_icu.config import API_KEY, ATHLETE_ID


def _parse_streams(value: str | None) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    streams = [part.strip().lower() for part in value.split(",") if part.strip()]
    return streams or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch sampled activity streams from intervals.icu for one activity."
    )
    parser.add_argument("--id", required=True, help="intervals.icu activity ID")
    parser.add_argument(
        "--streams",
        default="time,distance,altitude,heartrate,velocity",
        help="Comma-separated stream names, e.g. time,distance,heartrate.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=300,
        help="Maximum number of points retained after resampling (default: 300).",
    )
    parser.add_argument("--start-time-s", type=int, default=None, help="Optional start time in seconds")
    parser.add_argument("--end-time-s", type=int, default=None, help="Optional end time in seconds")
    parser.add_argument("--start-distance-m", type=float, default=None, help="Optional start distance in meters")
    parser.add_argument("--end-distance-m", type=float, default=None, help="Optional end distance in meters")
    args = parser.parse_args()

    if not (1 <= args.max_points <= 10000):
        print("Error: --max-points must be between 1 and 10000.", file=sys.stderr)
        raise SystemExit(1)

    try:
        result = fetch_sampled_streams(
            API_KEY,
            str(args.id),
            stream_types=_parse_streams(args.streams),
            max_points=args.max_points,
            start_time_s=args.start_time_s,
            end_time_s=args.end_time_s,
            start_distance_m=args.start_distance_m,
            end_distance_m=args.end_distance_m,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - CLI-level error handling
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
