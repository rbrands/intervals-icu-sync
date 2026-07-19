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
import tempfile
from datetime import date, timedelta
from pathlib import Path

# Allow running without the package installed in editable mode
_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))  # allow direct import of scripts

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
import upload_plan as _upload_plan  # direct import – no subprocess overhead
from intervals_icu.client import get_library_folders, get_library_workouts
from intervals_icu.config import API_KEY, ATHLETE_ID, STANDARD_LIBRARY_ATHLETE_ID
from intervals_icu.prompt_templates import render_coach_prompt
PROCESSED_DIR = _ROOT / "data" / "processed"
PLANS_DIR = _ROOT / "data" / "plans"

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "unknown"

# Build allowed_hosts: always include localhost variants, plus any extra host
# configured via FASTMCP_ALLOWED_HOST (e.g. the Cloudflare tunnel hostname).
_extra_host = os.environ.get("FASTMCP_ALLOWED_HOST", "")
_allowed_hosts: list[str] = ["127.0.0.1", "localhost"]
if _extra_host:
    _allowed_hosts.append(_extra_host)

mcp = FastMCP(
    "intervals-icu-coach",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
    transport_security=TransportSecuritySettings(allowed_hosts=_allowed_hosts),
)


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


def _run_script(
    script: str,
    timeout: int = 60,
    extra_env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Run a script from SCRIPTS_DIR. Returns (success, output)."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # prevent scripts from blocking on stdin
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    output = result.stdout + (f"\nSTDERR: {result.stderr}" if result.stderr.strip() else "")
    return result.returncode == 0, output.strip()


def _format_duration(seconds: int | float | None) -> str:
    total_seconds = int(seconds or 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _filter_activities_by_lookback(
    activities: list[dict] | None,
    *,
    current_date: date,
    lookback_days: int,
) -> list[dict]:
    if not activities:
        return []

    lower_bound = current_date - timedelta(days=lookback_days)
    filtered: list[dict] = []
    for activity in activities:
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue
        try:
            activity_date = date.fromisoformat(activity_date_str)
        except ValueError:
            continue
        if activity_date >= lower_bound:
            filtered.append(activity)
    return filtered


def _filter_fueling_analysis_by_lookback(
    fueling_data: dict | None,
    *,
    current_date: date,
    lookback_days: int,
) -> dict | None:
    if not isinstance(fueling_data, dict):
        return fueling_data

    activities = fueling_data.get("activities")
    if not isinstance(activities, list):
        return fueling_data

    filtered = _filter_activities_by_lookback(
        activities,
        current_date=current_date,
        lookback_days=lookback_days,
    )
    updated = dict(fueling_data)
    updated["activities"] = filtered
    return updated


def _merge_fueling_into_activities(
    activities: list[dict] | None,
    fueling_data: dict | None,
) -> tuple[list[dict], dict | None]:
    activity_list = activities if isinstance(activities, list) else []

    fueling_by_date: dict[str, list[dict]] = {}
    cleaned_fueling = fueling_data
    if isinstance(fueling_data, dict):
        fueling_activities = fueling_data.get("activities")
        if isinstance(fueling_activities, list):
            for entry in fueling_activities:
                if not isinstance(entry, dict):
                    continue
                entry_date = entry.get("date")
                if not isinstance(entry_date, str):
                    continue
                fueling_by_date.setdefault(entry_date, []).append(entry)
        cleaned_fueling = {k: v for k, v in fueling_data.items() if k != "activities"}

    merged_activities: list[dict] = []
    for activity in activity_list:
        date_key = activity.get("date")
        queue = fueling_by_date.get(date_key, []) if isinstance(date_key, str) else []
        fueling_match = queue.pop(0) if queue else None
        if isinstance(fueling_match, dict):
            fueling_match = {
                k: v
                for k, v in fueling_match.items()
                if k not in {"date", "name", "duration_hours"}
            }
        merged = dict(activity)
        merged["fueling"] = fueling_match
        merged_activities.append(merged)

    return merged_activities, cleaned_fueling


def _flatten_folders(nodes: list, parent_path: str = "") -> dict[int, str]:
    folder_map: dict[int, str] = {}
    for entry in nodes or []:
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


def _normalize_library_workouts(workouts: list, folder_map: dict[int, str]) -> list[dict]:
    rows = []
    for workout in workouts or []:
        if not isinstance(workout, dict):
            continue
        rows.append(
            {
                "folder": folder_map.get(workout.get("folder_id"), "-"),
                "name": workout.get("name") or "(unnamed)",
                "duration": _format_duration(workout.get("moving_time")),
                "duration_seconds": int(workout.get("moving_time") or 0),
                "tss": workout.get("icu_training_load") or 0,
                "tags": workout.get("tags") or [],
            }
        )
    rows.sort(key=lambda row: (row["folder"], row["name"].lower()))
    return rows


def _normalize_tag_prefixes(tag_prefixes: list[str] | str | None) -> list[str]:
    if tag_prefixes is None:
        return []
    if isinstance(tag_prefixes, str):
        values = [p.strip() for p in tag_prefixes.split(",")]
    else:
        values = [str(p).strip() for p in tag_prefixes]
    return [v.lower() for v in values if v]


def _apply_workout_filters(
    rows: list[dict],
    tag_prefixes: list[str] | str | None,
    match_mode: str,
    include_untagged: bool,
    limit: int,
) -> tuple[list[dict], list[str]]:
    prefixes = _normalize_tag_prefixes(tag_prefixes)

    if not prefixes:
        filtered = rows[:]
    else:
        filtered = []
        for row in rows:
            tags = [str(t).lower() for t in (row.get("tags") or [])]
            if not tags:
                if include_untagged:
                    filtered.append(row)
                continue

            if match_mode == "all":
                matches = all(any(tag.startswith(prefix) for tag in tags) for prefix in prefixes)
            else:
                matches = any(any(tag.startswith(prefix) for tag in tags) for prefix in prefixes)

            if matches:
                filtered.append(row)

    if limit > 0:
        filtered = filtered[:limit]

    return filtered, prefixes


def _is_shared_outgoing_folder(folder: dict) -> bool:
    visibility = (folder.get("visibility") or "").upper()
    shared_with_count = int(folder.get("sharedWithCount") or 0)
    has_share_token = bool(folder.get("shareToken"))
    return visibility == "PUBLIC" or shared_with_count > 0 or has_share_token


def _owner_label(folder: dict, fallback_athlete_id: str) -> str:
    owner = folder.get("owner")
    if isinstance(owner, dict):
        return owner.get("name") or owner.get("id") or fallback_athlete_id
    return fallback_athlete_id


def _collect_shared_outgoing_workouts(nodes: list, athlete_id: str, parent_path: str = "", shared_context: dict | None = None) -> list[dict]:
    results: list[dict] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")
        if node_type in {"FOLDER", "PLAN"}:
            name = node.get("name") or f"Folder {node.get('id')}"
            path = f"{parent_path} / {name}" if parent_path else name

            current_shared = shared_context
            if _is_shared_outgoing_folder(node):
                current_shared = {
                    "shared_from": _owner_label(node, athlete_id),
                    "folder_path": path,
                }

            children = node.get("children") or []
            results.extend(_collect_shared_outgoing_workouts(children, athlete_id, path, current_shared))
            continue

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


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp.prompt(title="Coach Prompt", description="Return a coaching prompt from prompts/library by prompt name.")
def coach_prompt(prompt_name: str = "", response_language: str = "de") -> str:
    """Return a coaching prompt from prompts/library."""
    return render_coach_prompt(prompt_name or None, response_language)


@mcp.prompt(title="Coach Prompt - Single Workout Analysis", description="Single workout analysis prompt from prompts/library.")
def coach_prompt_single_workout_analysis(response_language: str = "de") -> str:
    """Return the single workout analysis coaching prompt."""
    return render_coach_prompt("single_workout_analysis", response_language)


@mcp.prompt(title="Coach Prompt - Weekly Analysis", description="Weekly analysis prompt from prompts/library.")
def coach_prompt_weekly_analysis(response_language: str = "de") -> str:
    """Return the weekly analysis coaching prompt."""
    return render_coach_prompt("weekly_analysis", response_language)


@mcp.prompt(
    title="Coach Prompt - Training Plan Generation (Manual)",
    description="Manual training plan generation prompt from prompts/library.",
)
def coach_prompt_training_plan_generation_manual(response_language: str = "de") -> str:
    """Return the manual training plan generation coaching prompt."""
    return render_coach_prompt("training_plan_generation_manual", response_language)


@mcp.prompt(
    title="Coach Prompt - Training Plan Generation (Automatic)",
    description="Automatic training plan generation prompt from prompts/library.",
)
def coach_prompt_training_plan_generation_automatic(response_language: str = "de") -> str:
    """Return the automatic training plan generation coaching prompt."""
    return render_coach_prompt("training_plan_generation_automatic", response_language)


@mcp.prompt(title="Coach Prompt - Fueling Analysis", description="Fueling analysis prompt from prompts/library.")
def coach_prompt_fueling_analysis(response_language: str = "de") -> str:
    """Return the fueling analysis coaching prompt."""
    return render_coach_prompt("fueling_analysis", response_language)


@mcp.prompt(title="Coach Prompt - Metrics & Wellness Summary", description="Metrics and wellness summary prompt from prompts/library.")
def coach_prompt_metrics_wellness_summary(response_language: str = "de") -> str:
    """Return the metrics and wellness summary coaching prompt."""
    return render_coach_prompt("metrics_wellness_summary", response_language)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def prepare_week_data(lookback_days: int = 7) -> str:
    """Fetch all training data, run fueling/week analysis, and consolidate output.

    Activity and fueling details use a sliding window controlled by
    ``lookback_days`` (default: 7).
    Calendar-week anchored sections (e.g. ``week_summary`` and ``week_starting``)
    remain based on the current Monday.

    This tool runs the full pipeline:
    1. get_activities – fetches Garmin/manual rides from intervals.icu
    2. get_metrics    – fetches athlete performance metrics (CTL, ATL, form)
    3. get_training_plan – fetches the active training plan and weekly targets
    4. prepare_activities_for_coach – enriches activities with zone data
    5. prepare_planned_workouts_for_coach – adds upcoming planned workouts
    6. fueling_analysis – analyses carbohydrate intake quality
    7. analyze_week – computes Joe-Friel weekly summary
    8. consolidates all outputs into data/processed/coach_input_{monday}.json

    Args:
        lookback_days: Sliding-window size in days for activity/fueling data.
            Must be >= 1.

    Returns a status summary with the result of each step.
    """
    if lookback_days < 1:
        return "lookback_days must be >= 1"

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
        per_script_env = {"LOOKBACK_DAYS": str(lookback_days)} if script in {
            "prepare_activities_for_coach.py",
            "fueling_analysis.py",
        } else None
        ok, output = _run_script(script, extra_env=per_script_env)
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

    def _copy_target_fields(entry: dict, target: dict) -> None:
        load_target = target.get("load_target")
        time_target_hours = target.get("time_target_hours")
        if load_target is not None:
            entry["weekly_load_target"] = load_target
        if time_target_hours is not None:
            entry["weekly_time_target_hours"] = time_target_hours

    # Embed Ride training plan info
    if plan_data:
        phases = [p for p in (plan_data.get("active_phases") or []) if p.get("sport_type") == "Ride"]
        next_phases = [p for p in (plan_data.get("next_week_active_phases") or []) if p.get("sport_type") == "Ride"]
        ride_plan: list[dict] = []
        for targets_key, constraints_key, week_monday, phase_list in [
            ("weekly_load_targets", "weekly_day_constraints", monday, phases),
            (
                "next_week_load_targets",
                "next_week_day_constraints",
                monday + timedelta(weeks=1),
                next_phases,
            ),
        ]:
            targets = [t for t in (plan_data.get(targets_key) or []) if t.get("sport_type") == "Ride"]
            week_constraints = plan_data.get(constraints_key) or []
            if not phase_list and not targets and not week_constraints:
                continue
            entry: dict = {"week": week_monday.isoformat()}
            if phase_list:
                p = phase_list[0]
                entry.update({k: p.get(k) for k in ("plan_name", "phase", "start", "end")})
            if targets:
                t = targets[0]
                _copy_target_fields(entry, t)
                entry["week_type"] = t.get("week_type", "NORMAL")
                if t.get("week_note"):
                    entry["week_note"] = t["week_note"]
            if week_constraints:
                entry["day_constraints"] = week_constraints
            ride_plan.append(entry)
        if ride_plan:
            if not isinstance(week_data, dict):
                week_data = {}
            week_data["training_plan"] = ride_plan

    activities = activities_data if isinstance(activities_data, list) else (activities_data or {}).get("activities")
    activities = _filter_activities_by_lookback(
        activities if isinstance(activities, list) else [],
        current_date=today,
        lookback_days=lookback_days,
    )
    fueling_data = _filter_fueling_analysis_by_lookback(
        fueling_data if isinstance(fueling_data, dict) else None,
        current_date=today,
        lookback_days=lookback_days,
    )
    activities, fueling_data = _merge_fueling_into_activities(activities, fueling_data)

    coach_input = {
        "schema_version": _SCHEMA_VERSION,
        "week_starting": monday_str,
        "lookback_days": lookback_days,
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
def list_library_workouts(
    tag_prefixes: list[str] | str | None = None,
    match_mode: str = "any",
    include_untagged: bool = False,
    limit: int = 500,
) -> str:
    """List own library workouts for the configured athlete (ATHLETE_ID).

    Returns folder, name, duration, TSS and tags for each workout.

    Args:
        tag_prefixes: Optional tag prefix filter (e.g. ["aerobic-threshold-", "lactate-threshold-"]).
        match_mode: "any" (default) or "all" when multiple prefixes are provided.
        include_untagged: Include workouts without tags when tag_prefixes is set.
        limit: Maximum number of rows to return (1-5000).
    """
    if match_mode not in {"any", "all"}:
        return json.dumps({"error": "match_mode must be 'any' or 'all'"}, ensure_ascii=False)
    if limit < 1 or limit > 5000:
        return json.dumps({"error": "limit must be between 1 and 5000"}, ensure_ascii=False)

    folders = get_library_folders(API_KEY, ATHLETE_ID)
    workouts = get_library_workouts(API_KEY, ATHLETE_ID)
    folder_map = _flatten_folders(folders)
    normalized = _normalize_library_workouts(workouts, folder_map)
    filtered, normalized_prefixes = _apply_workout_filters(
        normalized,
        tag_prefixes,
        match_mode,
        include_untagged,
        limit,
    )

    return json.dumps(
        {
            "schema_version": _SCHEMA_VERSION,
            "athlete_id": ATHLETE_ID,
            "total_workouts": len(normalized),
            "returned": len(filtered),
            "filters": {
                "tag_prefixes": normalized_prefixes,
                "match_mode": match_mode,
                "include_untagged": include_untagged,
                "limit": limit,
            },
            "workouts": filtered,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def list_standard_library_workouts(
    tag_prefixes: list[str] | str | None = None,
    match_mode: str = "any",
    include_untagged: bool = False,
    limit: int = 500,
) -> str:
    """List workouts shared by STANDARD_LIBRARY_ATHLETE_ID.

    Uses the optional config value STANDARD_LIBRARY_ATHLETE_ID from .env.

    Args:
        tag_prefixes: Optional tag prefix filter (e.g. ["aerobic-threshold-", "lactate-threshold-"]).
        match_mode: "any" (default) or "all" when multiple prefixes are provided.
        include_untagged: Include workouts without tags when tag_prefixes is set.
        limit: Maximum number of rows to return (1-5000).
    """
    if match_mode not in {"any", "all"}:
        return json.dumps({"error": "match_mode must be 'any' or 'all'"}, ensure_ascii=False)
    if limit < 1 or limit > 5000:
        return json.dumps({"error": "limit must be between 1 and 5000"}, ensure_ascii=False)

    standard_athlete_id = STANDARD_LIBRARY_ATHLETE_ID.strip()
    if not standard_athlete_id:
        return json.dumps(
            {
                "error": "STANDARD_LIBRARY_ATHLETE_ID is not set in .env",
                "hint": "Set STANDARD_LIBRARY_ATHLETE_ID to the athlete id whose shared library should be listed.",
            },
            ensure_ascii=False,
        )

    folders = get_library_folders(API_KEY, standard_athlete_id)
    shared_rows = _collect_shared_outgoing_workouts(folders, standard_athlete_id)
    shared_rows.sort(key=lambda row: (row["shared_from"], row["folder"], row["name"].lower()))
    filtered, normalized_prefixes = _apply_workout_filters(
        shared_rows,
        tag_prefixes,
        match_mode,
        include_untagged,
        limit,
    )

    return json.dumps(
        {
            "schema_version": _SCHEMA_VERSION,
            "standard_library_athlete_id": standard_athlete_id,
            "total_workouts": len(shared_rows),
            "returned": len(filtered),
            "filters": {
                "tag_prefixes": normalized_prefixes,
                "match_mode": match_mode,
                "include_untagged": include_untagged,
                "limit": limit,
            },
            "workouts": filtered,
        },
        ensure_ascii=False,
    )


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
def validate_week_plan(plan_json: str = "", max_errors: int = 10) -> str:
    """Validate a training plan JSON against the upload schema.

    If plan_json is provided, the tool validates that inline payload.
    If omitted, the tool validates data/plans/week_plan.json.

    Args:
        plan_json: Optional plan JSON string to validate.
        max_errors: Maximum number of schema errors to include (>= 1).
    """
    if max_errors < 1:
        return json.dumps({"error": "max_errors must be >= 1"}, ensure_ascii=False)

    schema_path = _ROOT / "contracts" / "week-plan" / "week-plan.schema.json"
    validate_script = SCRIPTS_DIR / "validate_plan.py"

    plan_source = "saved"
    temp_plan_path: Path | None = None

    if plan_json.strip():
        plan_source = "inline"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(plan_json)
            temp_plan_path = Path(tmp.name)
        plan_path = temp_plan_path
    else:
        plan_path = PLANS_DIR / "week_plan.json"
        if not plan_path.exists():
            return json.dumps(
                {"error": "No week_plan.json found in data/plans/. Run save_week_plan first or pass plan_json."},
                ensure_ascii=False,
            )

    try:
        cmd = [
            sys.executable,
            str(validate_script),
            "--plan",
            str(plan_path),
            "--schema",
            str(schema_path),
            "--max-errors",
            str(max_errors),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        output = (result.stdout or "") + (f"\nSTDERR: {result.stderr}" if (result.stderr or "").strip() else "")
        output = output.strip()

        if result.returncode == 0:
            return json.dumps(
                {
                    "status": "valid",
                    "plan_source": plan_source,
                    "schema": "contracts/week-plan/week-plan.schema.json",
                    "details": output,
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "status": "invalid",
                "plan_source": plan_source,
                "schema": "contracts/week-plan/week-plan.schema.json",
                "details": output or "Validation failed.",
            },
            ensure_ascii=False,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Validation timed out after 30s"}, ensure_ascii=False)
    finally:
        if temp_plan_path is not None:
            temp_plan_path.unlink(missing_ok=True)


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
