"""Quick local smoke-test for the MCP tool functions.

Reads credentials from the project .env file and calls the tool functions
directly (no HTTP / SSE needed). The server does NOT need to be running.

Usage (from repo root, venv active):
    python webservice/test_tools.py
    python webservice/test_tools.py upload_plan
"""

import json
import sys
from pathlib import Path

# Allow imports from src/ and webservice/
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "webservice"))

# Load .env so ATHLETE_ID / INTERVALS_API_KEY are available
from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")
import os

from context import api_key_var, athlete_id_var
import mcp_server as srv


def _inject_credentials() -> tuple:
    athlete_id = os.environ.get("ATHLETE_ID", "")
    api_key = os.environ.get("INTERVALS_API_KEY", "")
    if not athlete_id or not api_key:
        print("ERROR: ATHLETE_ID or INTERVALS_API_KEY not set in .env")
        sys.exit(1)
    t1 = athlete_id_var.set(athlete_id)
    t2 = api_key_var.set(api_key)
    return t1, t2


def test_prepare_week() -> None:
    print("=== prepare_week_for_coach ===")
    t1, t2 = _inject_credentials()
    try:
        result = srv.prepare_week_for_coach()
        data = json.loads(result)
        if "error" in data:
            print("FAILED:", json.dumps(data, indent=2, ensure_ascii=False))
        else:
            # Print a short summary instead of the full JSON
            print(f"schema_version : {data.get('schema_version')}")
            print(f"week_starting  : {data.get('week_starting')}")
            print(f"current_date   : {data.get('current_date')}")
            acts = data.get("activities") or []
            print(f"activities     : {len(acts)}")
            metrics = data.get("metrics") or {}
            print(f"ctl            : {metrics.get('ctl')}")
            print(f"atl            : {metrics.get('atl')}")
            print(f"tsb            : {metrics.get('tsb')}")
            print("\nFull JSON written to: /tmp/coach_input_test.json")
            Path("/tmp/coach_input_test.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
    finally:
        athlete_id_var.reset(t1)
        api_key_var.reset(t2)


def test_upload_plan_dry_run() -> None:
    print("=== upload_plan (dry_run=True) ===")
    t1, t2 = _inject_credentials()
    sample_plan = json.dumps([
        {
            "date": "2026-05-19T09:00:00",
            "name": "Test Endurance Ride",
            "duration_minutes": 60,
            "description": "Zone 2 smoke-test",
        }
    ])
    try:
        result = srv.upload_plan(plan_json=sample_plan, dry_run=True)
        print(result)
    finally:
        athlete_id_var.reset(t1)
        api_key_var.reset(t2)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prepare_week"
    if cmd == "upload_plan":
        test_upload_plan_dry_run()
    else:
        test_prepare_week()
