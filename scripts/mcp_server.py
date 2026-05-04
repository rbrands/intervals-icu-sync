"""MCP server exposing intervals.icu weekly training data as tools and resources.

Run with:
    python scripts/mcp_server.py

Or via the MCP CLI (after installing mcp[cli]):
    mcp run scripts/mcp_server.py

Configure in Claude Desktop / VS Code Copilot by pointing to this file.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running without the package installed in editable mode
_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))  # allow direct import of scripts

from mcp.server.fastmcp import FastMCP
import upload_plan as _upload_plan  # direct import – no subprocess overhead
PROCESSED_DIR = _ROOT / "data" / "processed"
PLANS_DIR = _ROOT / "data" / "plans"

mcp = FastMCP("intervals-icu-coach")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _resolve_monday(monday: str | None) -> date:
    """Parse an ISO-date string or return the current week's Monday."""
    if monday:
        return date.fromisoformat(monday)
    return _current_monday()


def _load_json_file(path: Path) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _run_script(script: str) -> tuple[bool, str]:
    """Run a script from SCRIPTS_DIR. Returns (success, output)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        capture_output=True,
        text=True,
    )
    output = result.stdout + (f"\nSTDERR: {result.stderr}" if result.stderr.strip() else "")
    return result.returncode == 0, output.strip()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def prepare_week_data() -> str:
    """Fetch all training data for the current week from intervals.icu, run fueling
    and week analysis, and consolidate everything into a coach_input JSON file.

    This tool runs the full pipeline:
    1. get_activities – fetches Garmin/manual rides from intervals.icu
    2. get_metrics    – fetches athlete performance metrics (CTL, ATL, form)
    3. get_training_plan – fetches the active training plan and weekly targets
    4. prepare_activities_for_coach – enriches activities with zone data
    5. prepare_planned_workouts_for_coach – adds upcoming planned workouts
    6. fueling_analysis – analyses carbohydrate intake quality
    7. analyze_week – computes Joe-Friel weekly summary
    8. consolidates all outputs into data/processed/coach_input_{monday}.json

    Returns a status summary with the result of each step.
    """
    pipeline = [
        "get_activities.py",
        "get_metrics.py",
        "get_training_plan.py",
        "prepare_activities_for_coach.py",
        "prepare_planned_workouts_for_coach.py",
        "fueling_analysis.py",
        "analyze_week.py",
    ]

    lines: list[str] = []
    for script in pipeline:
        ok, output = _run_script(script)
        status = "OK" if ok else "FAILED"
        lines.append(f"[{status}] {script}")
        if output:
            lines.append(f"       {output[:300]}")
        if not ok:
            lines.append("\nPipeline aborted.")
            return "\n".join(lines)

    # Consolidation (inline from prepare_week_for_coach.py)
    today = date.today()
    monday = _current_monday()
    monday_str = monday.isoformat()

    metrics_files = sorted(PROCESSED_DIR.glob("metrics_*.json"))
    metrics = json.loads(metrics_files[-1].read_text(encoding="utf-8")) if metrics_files else None

    activities_data = _load_json_file(PROCESSED_DIR / f"coach_input_{monday_str}.json")
    fueling_data = _load_json_file(PROCESSED_DIR / f"fueling_analysis_{monday_str}.json")
    week_data = _load_json_file(PROCESSED_DIR / f"week_summary_{monday_str}.json")
    plan_data = _load_json_file(PROCESSED_DIR / f"training_plan_{today.isoformat()}.json")
    planned_workouts_data = _load_json_file(PROCESSED_DIR / f"planned_workouts_{monday_str}.json")

    # Embed Ride training plan info
    if plan_data:
        phases = [p for p in (plan_data.get("active_phases") or []) if p.get("sport_type") == "Ride"]
        next_phases = [p for p in (plan_data.get("next_week_active_phases") or []) if p.get("sport_type") == "Ride"]
        ride_plan: list[dict] = []
        for targets_key, week_monday, phase_list in [
            ("weekly_load_targets", monday, phases),
            ("next_week_load_targets", monday + timedelta(weeks=1), next_phases or phases),
        ]:
            targets = [t for t in (plan_data.get(targets_key) or []) if t.get("sport_type") == "Ride"]
            if not phase_list and not targets:
                continue
            entry: dict = {"week": week_monday.isoformat()}
            if phase_list:
                p = phase_list[0]
                entry.update({k: p.get(k) for k in ("plan_name", "phase", "start", "end")})
            if targets:
                t = targets[0]
                entry["weekly_load_target"] = t.get("load_target")
                entry["week_type"] = t.get("week_type", "NORMAL")
                entry["training_availability"] = t.get("training_availability", "NORMAL")
                if t.get("week_note"):
                    entry["week_note"] = t["week_note"]
            ride_plan.append(entry)
        if ride_plan:
            if not isinstance(week_data, dict):
                week_data = {}
            week_data["training_plan"] = ride_plan

    activities = activities_data if isinstance(activities_data, list) else (activities_data or {}).get("activities")

    coach_input = {
        "week_starting": monday_str,
        "current_date": today.isoformat(),
        "metrics": metrics,
        "week_summary": week_data,
        "activities": activities,
        "fueling_analysis": fueling_data,
        "planned_workouts": planned_workouts_data,
    }

    output_file = PROCESSED_DIR / f"coach_input_{monday_str}.json"
    output_file.write_text(json.dumps(coach_input, indent=2, ensure_ascii=False), encoding="utf-8")

    lines.append(f"\n[OK] Consolidated → {output_file.name}")
    lines.append("Pipeline completed successfully.")
    return "\n".join(lines)


@mcp.tool()
def get_coach_input(monday: str = "") -> str:
    """Return the consolidated weekly coach input as JSON.

    Contains activities, metrics (CTL/ATL/form), fueling analysis, week summary,
    and planned workouts for the specified week.

    Args:
        monday: ISO date string of the week's Monday (e.g. "2026-04-28").
                Defaults to the current week if omitted or empty.
    """
    week_monday = _resolve_monday(monday or None)
    path = PROCESSED_DIR / f"coach_input_{week_monday.isoformat()}.json"
    if not path.exists():
        return json.dumps({
            "error": f"No coach_input found for week {week_monday.isoformat()}. "
                     "Run the prepare_week_data tool first."
        }, ensure_ascii=False)
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_fueling_analysis(monday: str = "") -> str:
    """Return the carbohydrate fueling analysis for the specified week as JSON.

    Each activity is rated by carbs-per-hour and fueling ratio, with an overall
    weekly assessment and actionable recommendations.

    Args:
        monday: ISO date string of the week's Monday (e.g. "2026-04-28").
                Defaults to the current week if omitted or empty.
    """
    week_monday = _resolve_monday(monday or None)
    path = PROCESSED_DIR / f"fueling_analysis_{week_monday.isoformat()}.json"
    if not path.exists():
        return json.dumps({
            "error": f"No fueling_analysis found for week {week_monday.isoformat()}. "
                     "Run the prepare_week_data tool first."
        }, ensure_ascii=False)
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_latest_metrics() -> str:
    """Return the most recent athlete performance metrics as JSON.

    Includes CTL (chronic training load / fitness), ATL (acute training load /
    fatigue), TSB (training stress balance / form), and other intervals.icu
    wellness metrics.
    """
    files = sorted(PROCESSED_DIR.glob("metrics_*.json"))
    if not files:
        return json.dumps({
            "error": "No metrics files found. Run the prepare_week_data tool first."
        }, ensure_ascii=False)
    return files[-1].read_text(encoding="utf-8")


@mcp.tool()
def save_week_plan(plan_json: str) -> str:
    """Save a weekly training plan as JSON to data/plans/week_plan.json.

    Use this after the AI coach has generated the week plan. The saved file
    can then be uploaded to intervals.icu with the upload_week_plan tool.

    Args:
        plan_json: The training plan as a JSON string. Must be a JSON array of
                   workout objects or an object with a "workouts" array. Each
                   workout must have "date", "name", and "duration_minutes".
                   Example:
                   [
                     {
                       "date": "2026-05-05T09:00:00",
                       "name": "Endurance Ride",
                       "duration_minutes": 90,
                       "description": "Zone 2 steady state",
                       "tags": ["endurance-moderate"]
                     }
                   ]
    """
    try:
        data = json.loads(plan_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"}, ensure_ascii=False)

    workouts = data if isinstance(data, list) else data.get("workouts") if isinstance(data, dict) else None
    if workouts is None:
        return json.dumps({
            "error": "plan_json must be a JSON array or an object with a 'workouts' array."
        }, ensure_ascii=False)

    missing_fields: list[str] = []
    for i, w in enumerate(workouts):
        for field in ("date", "name", "duration_minutes"):
            if w.get(field) is None:
                missing_fields.append(f"entry {i + 1}: missing '{field}'")
    if missing_fields:
        return json.dumps({"error": "Validation failed", "details": missing_fields}, ensure_ascii=False)

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    output = PLANS_DIR / "week_plan.json"
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    count = len(workouts)
    return json.dumps({
        "status": "saved",
        "file": "data/plans/week_plan.json",
        "workouts": count,
        "message": f"{count} workout(s) saved. Run upload_week_plan to push to intervals.icu.",
    }, ensure_ascii=False)


@mcp.tool()
def upload_week_plan(dry_run: bool = False, clear: bool = False) -> str:
    """Upload the saved weekly training plan to intervals.icu.

    Reads data/plans/week_plan.json and creates or updates WORKOUT events in
    the intervals.icu calendar. Existing events with the same name and date are
    updated (PUT), new ones are created (POST) — no duplicates.

    Typically called after save_week_plan has written the coach's plan.

    Args:
        dry_run: If True, print what would be uploaded without making API calls.
        clear:   If True, delete all existing WORKOUT events for the plan's date
                 range before uploading (useful to fix duplicates).
    """
    plan_path = PLANS_DIR / "week_plan.json"
    if not plan_path.exists():
        return json.dumps({
            "error": "No week_plan.json found in data/plans/. Run save_week_plan first."
        }, ensure_ascii=False)

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            plan, week = _upload_plan.load_plan(plan_path)
            print(f"Found {len(plan)} workout(s)\n")
            _upload_plan.upload_plan(plan, week=week, dry_run=dry_run, clear=clear)
    except SystemExit as exc:
        output = buf.getvalue()
        return output or json.dumps(
            {"error": f"Upload failed (exit code {exc.code})"}, ensure_ascii=False
        )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("coach://input/current")
def resource_current_coach_input() -> str:
    """Current week's consolidated coach input (activities, metrics, fueling, plan)."""
    path = PROCESSED_DIR / f"coach_input_{_current_monday().isoformat()}.json"
    if not path.exists():
        return json.dumps({"error": "No data for current week. Run prepare_week_data first."})
    return path.read_text(encoding="utf-8")


@mcp.resource("coach://fueling/current")
def resource_current_fueling() -> str:
    """Current week's carbohydrate fueling analysis."""
    path = PROCESSED_DIR / f"fueling_analysis_{_current_monday().isoformat()}.json"
    if not path.exists():
        return json.dumps({"error": "No fueling analysis for current week. Run prepare_week_data first."})
    return path.read_text(encoding="utf-8")


@mcp.resource("coach://metrics/latest")
def resource_latest_metrics() -> str:
    """Most recent athlete performance metrics (CTL, ATL, TSB)."""
    files = sorted(PROCESSED_DIR.glob("metrics_*.json"))
    if not files:
        return json.dumps({"error": "No metrics files found. Run prepare_week_data first."})
    return files[-1].read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        # SSE mode: exposes /sse and /messages/ endpoints for ChatGPT and other HTTP clients.
        # Configure host/port via FASTMCP_HOST and FASTMCP_PORT (defaults: 127.0.0.1:8000).
        # For ChatGPT you need a publicly reachable URL — forward with e.g. `ngrok http 8765`.
        #
        # Example:
        #   $env:MCP_TRANSPORT="sse"; $env:FASTMCP_HOST="127.0.0.1"; $env:FASTMCP_PORT="8765"
        #   python scripts/mcp_server.py
        mcp.run(transport="sse")
    else:
        # stdio mode (default): used by Claude Desktop and other local MCP clients.
        mcp.run(transport="stdio")
