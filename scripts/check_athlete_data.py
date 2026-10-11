"""Check an existing consolidated coach-input export without API calls.

Usage:
    python scripts/check_athlete_data.py
    python scripts/check_athlete_data.py --input data/processed/coach_input_2026-10-05.json
    python scripts/check_athlete_data.py --json
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intervals_icu.data_quality import check_athlete_data_json


def main() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    default_input = ROOT / "data" / "processed" / f"coach_input_{monday.isoformat()}.json"
    parser = argparse.ArgumentParser(
        description="Check consolidated athlete data for completeness and consistency.",
    )
    parser.add_argument(
        "--input", type=Path, default=default_input,
        help="Consolidated coach-input JSON (default: current week's data/processed export).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the structured JSON report instead of text.",
    )
    args = parser.parse_args()
    try:
        result = check_athlete_data_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    report = json.loads(result)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else report["report_text"])


if __name__ == "__main__":
    main()
