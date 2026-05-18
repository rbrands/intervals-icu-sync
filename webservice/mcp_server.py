"""MCP server for Azure App Service deployment.

Exposes two MCP tools over SSE transport:
  - prepare_week_for_coach  – runs the full data pipeline and returns the
                              consolidated coach input as JSON
  - upload_plan             – uploads a JSON training plan to intervals.icu

Credentials are passed per-request via HTTP headers (never stored on the server):
  X-Intervals-Athlete-Id   – athlete ID (e.g. "i12345")
  X-Intervals-Api-Key      – intervals.icu API key

Run locally (SSE mode):
    # Linux / macOS:
    MCP_TRANSPORT=sse python webservice/mcp_server.py
    # Windows (PowerShell):
    $env:MCP_TRANSPORT="sse"; python webservice/mcp_server.py

App Service startup command:
    python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000
"""

import json
import os
import subprocess
import sys
import contextlib
import tempfile
from datetime import date, timedelta
from pathlib import Path

# Repo root and scripts directory (unchanged from the existing layout)
_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = _ROOT / "scripts"
PROCESSED_DIR = _ROOT / "data" / "processed"

# Load .env when present (local dev only; has no effect on App Service)
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed – fine in production

# Application Insights telemetry (no-op if connection string is not set).
# On Azure App Service (WEBSITE_INSTANCE_ID is set), Managed Identity is used for
# authentication so the connection string cannot be abused as a write credential.
# Locally, key-based auth is used as a fallback.
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        if os.environ.get("WEBSITE_INSTANCE_ID"):  # running on Azure App Service
            from azure.identity import ManagedIdentityCredential
            configure_azure_monitor(credential=ManagedIdentityCredential())
        else:
            configure_azure_monitor()
except ImportError:
    pass  # azure-monitor-opentelemetry not installed – fine in local dev

# OpenTelemetry tracer for MCP tool spans (no-op when OTel is not available)
class _NoOpSpan:
    def set_attribute(self, *a, **kw): pass
    def set_status(self, *a, **kw): pass
    def record_exception(self, *a, **kw): pass

try:
    from opentelemetry import trace as _otel_trace
    _tracer = _otel_trace.get_tracer(__name__)
    _OK = _otel_trace.StatusCode.OK
    _ERROR = _otel_trace.StatusCode.ERROR
except ImportError:
    _tracer = None
    _OK = None
    _ERROR = None

@contextlib.contextmanager
def _tool_span(name: str):
    """Context manager for an OTel span; falls back to a no-op if OTel is unavailable."""
    if _tracer is not None:
        with _tracer.start_as_current_span(name) as span:
            yield span
    else:
        yield _NoOpSpan()

# Allow imports from src/ and from this package when run directly
sys.path.insert(0, str(_ROOT / "src"))
_WEBSERVICE_DIR = Path(__file__).resolve().parent
if str(_WEBSERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_WEBSERVICE_DIR))

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from context import api_key_var, athlete_id_var

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = (
    _VERSION_FILE.read_text(encoding="utf-8").strip()
    if _VERSION_FILE.exists()
    else "unknown"
)

# allowed_hosts: always include localhost variants (with and without port) plus
# the App Service hostname set via FASTMCP_ALLOWED_HOST (e.g. "myapp.azurewebsites.net").
# The Host header sent by clients includes the port (e.g. "localhost:8000"), so
# both forms must be listed.
_extra_host = os.environ.get("FASTMCP_ALLOWED_HOST", "")
_port = int(os.environ.get("FASTMCP_PORT", "8000"))
_allowed_hosts: list[str] = [
    "127.0.0.1",
    "localhost",
    f"127.0.0.1:{_port}",
    f"localhost:{_port}",
]
if _extra_host:
    _allowed_hosts.append(_extra_host)

# allowed_origins: localhost:* covers any port (MCP Inspector, VS Code, etc.).
# Localhost origins can only come from the local machine, so this is safe in
# all environments. The wildcard "http://localhost:*" is supported by the SDK's
# _validate_origin() method.
_allowed_origins: list[str] = ["http://localhost:*", "https://localhost:*"]
if _extra_host:
    _allowed_origins.append(f"https://{_extra_host}")

mcp = FastMCP(
    "intervals-icu-coach",
    host=os.environ.get("FASTMCP_HOST", "0.0.0.0"),
    port=_port,
    transport_security=TransportSecuritySettings(
        allowed_hosts=_allowed_hosts,
        allowed_origins=_allowed_origins,
    ),
)


# ---------------------------------------------------------------------------
# Pure ASGI middleware – extracts credentials from request headers
# ---------------------------------------------------------------------------

_DEV_MODE: bool = bool(os.environ.get("INTERVALS_DEV_MODE"))


class AuthHeaderMiddleware:
    """Reads X-Intervals-Athlete-Id and X-Intervals-Api-Key from incoming HTTP
    headers and stores them in ContextVars for the duration of the request.

    Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so that SSE
    streaming responses are never buffered.

    Always available:
    - GET /health  – returns JSON {status, schema_version, dev_mode, timestamp}.
      Suitable as an Azure App Service health-check path.

    Dev mode only (INTERVALS_DEV_MODE=true):
    - When credential headers are absent, falls back to ATHLETE_ID /
      INTERVALS_API_KEY environment variables (loaded from .env locally).
      Never enable this in production.
    """

    def __init__(self, asgi_app) -> None:
        self._asgi_app = asgi_app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            # Health endpoints (also handles /sse/health for MCP Inspector probe)
            if path in ("/health", "/sse/health"):
                await self._handle_health(scope, receive, send)
                return
            # Config probe used by MCP Inspector – return a minimal discovery doc
            if path == "/sse/config":
                await self._handle_sse_config(scope, receive, send)
                return

        if scope["type"] in ("http", "websocket"):
            header_dict = {k.lower(): v for k, v in scope.get("headers", [])}
            athlete_id = header_dict.get(
                b"x-intervals-athlete-id", b""
            ).decode("utf-8", errors="replace")
            api_key = header_dict.get(
                b"x-intervals-api-key", b""
            ).decode("utf-8", errors="replace")

            # Dev-mode fallback: use .env / process env when headers are missing
            if _DEV_MODE and (not athlete_id or not api_key):
                athlete_id = athlete_id or os.environ.get("ATHLETE_ID", "")
                api_key = api_key or os.environ.get("INTERVALS_API_KEY", "")

            token_a = athlete_id_var.set(athlete_id)
            token_k = api_key_var.set(api_key)
            try:
                await self._asgi_app(scope, receive, send)
            finally:
                athlete_id_var.reset(token_a)
                api_key_var.reset(token_k)
        else:
            await self._asgi_app(scope, receive, send)

    @staticmethod
    async def _handle_sse_config(scope, receive, send) -> None:  # noqa: ARG004
        """Return a minimal SSE config document expected by MCP Inspector."""
        body = json.dumps(
            {"name": "intervals-icu-coach", "version": _SCHEMA_VERSION, "transport": "sse"},
            ensure_ascii=False,
        ).encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [[b"content-type", b"application/json"],
                                 [b"content-length", str(len(body)).encode()]]})
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    async def _handle_health(scope, receive, send) -> None:  # noqa: ARG004
        import datetime
        body = json.dumps(
            {
                "status": "ok",
                "schema_version": _SCHEMA_VERSION,
                "dev_mode": _DEV_MODE,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        ).encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [[b"content-type", b"application/json"],
                                 [b"content-length", str(len(body)).encode()]]})
        await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_credentials() -> tuple[str, str]:
    """Return (athlete_id, api_key) from the current request's ContextVars."""
    return athlete_id_var.get(), api_key_var.get()


def _check_credentials() -> str | None:
    """Return an error JSON string when credentials are missing, else None."""
    athlete_id, api_key = _get_credentials()
    if not athlete_id or not api_key:
        return json.dumps(
            {
                "error": (
                    "Missing credentials. "
                    "Pass X-Intervals-Athlete-Id and X-Intervals-Api-Key headers."
                )
            },
            ensure_ascii=False,
        )
    return None


def _run_script(
    script: str,
    timeout: int = 120,
    extra_env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Run a script from SCRIPTS_DIR, injecting credentials as env vars."""
    athlete_id, api_key = _get_credentials()
    env = os.environ.copy()
    env["INTERVALS_API_KEY"] = api_key
    env["ATHLETE_ID"] = athlete_id
    if extra_env:
        env.update(extra_env)
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    output = result.stdout + (
        f"\nSTDERR: {result.stderr}" if result.stderr.strip() else ""
    )
    return result.returncode == 0, output.strip()


def _load_json_file(path: Path) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _extract_ride_plan_summary(plan_data: dict | None, monday: date) -> list[dict]:
    """Return Ride-only training plan entries for the current and next week."""
    if not plan_data:
        return []

    phases = [
        p for p in (plan_data.get("active_phases") or [])
        if p.get("sport_type") == "Ride"
    ]
    next_phases = [
        p for p in (plan_data.get("next_week_active_phases") or [])
        if p.get("sport_type") == "Ride"
    ]

    def _build(targets_key: str, week_monday: date, phase_list: list) -> dict | None:
        targets = [
            t for t in (plan_data.get(targets_key) or [])
            if t.get("sport_type") == "Ride"
        ]
        if not phase_list and not targets:
            return None
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
        return entry

    result: list[dict] = []
    current = _build("weekly_load_targets", monday, phases)
    if current:
        result.append(current)
    nxt = _build(
        "next_week_load_targets", monday + timedelta(weeks=1), next_phases or phases
    )
    if nxt:
        result.append(nxt)
    return result


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def prepare_week_data() -> str:
    """Fetch all training data for the current week from intervals.icu, run the
    full analysis pipeline, and return the consolidated coach input as JSON.

    Pipeline steps:
    1. get_activities               – fetch Garmin/manual rides
    2. get_metrics                  – fetch CTL, ATL, TSB, HRV, VO2max
    3. get_training_plan            – fetch active training plan and weekly targets
    4. prepare_activities_for_coach – enrich activities with zone data and W'bal
    5. prepare_planned_workouts_for_coach – add upcoming planned workouts
    6. fueling_analysis             – analyse carbohydrate intake quality
    7. analyze_week                 – compute Joe-Friel weekly summary

    Returns the consolidated JSON directly. Nothing is persisted on the server
    beyond the duration of this call.

    Credentials are read from the X-Intervals-Athlete-Id and X-Intervals-Api-Key
    request headers.
    """
    with _tool_span("mcp.tool/prepare_week_data") as span:
        err = _check_credentials()
        if err:
            span.set_status(_ERROR, "missing credentials")
            return err

        pipeline = [
            "get_activities.py",
            "get_metrics.py",
            "get_training_plan.py",
            "prepare_activities_for_coach.py",
            "prepare_planned_workouts_for_coach.py",
            "fueling_analysis.py",
            "analyze_week.py",
        ]

        # Each request writes to its own isolated temp directories so that
        # concurrent requests for different athletes never overwrite each other.
        with tempfile.TemporaryDirectory(prefix="intervals_raw_") as tmp_raw, \
             tempfile.TemporaryDirectory(prefix="intervals_proc_") as tmp_proc:

            tmp_raw_path = Path(tmp_raw)
            tmp_proc_path = Path(tmp_proc)
            extra_env = {
                "INTERVALS_RAW_DIR": str(tmp_raw_path),
                "INTERVALS_PROCESSED_DIR": str(tmp_proc_path),
            }

            log_lines: list[str] = []
            for script in pipeline:
                ok, output = _run_script(script, extra_env=extra_env)
                status = "OK" if ok else "FAILED"
                log_lines.append(f"[{status}] {script}")
                if output:
                    log_lines.append(f"       {output[:300]}")
                if not ok:
                    span.set_status(_ERROR, f"pipeline failed at {script}")
                    return json.dumps(
                        {
                            "error": f"Pipeline failed at {script}",
                            "log": "\n".join(log_lines),
                        },
                        ensure_ascii=False,
                    )

            # Consolidate outputs from the isolated temp directory
            today = date.today()
            monday = _current_monday()
            monday_str = monday.isoformat()

            metrics_files = sorted(tmp_proc_path.glob("metrics_*.json"))
            metrics = (
                json.loads(metrics_files[-1].read_text(encoding="utf-8"))
                if metrics_files
                else None
            )

            activities_data = _load_json_file(tmp_proc_path / f"coach_input_{monday_str}.json")
            fueling_data = _load_json_file(
                tmp_proc_path / f"fueling_analysis_{monday_str}.json"
            )
            week_data = _load_json_file(tmp_proc_path / f"week_summary_{monday_str}.json")
            plan_data = _load_json_file(
                tmp_proc_path / f"training_plan_{today.isoformat()}.json"
            )
            planned_workouts_data = _load_json_file(
                tmp_proc_path / f"planned_workouts_{monday_str}.json"
            )

            ride_plan = _extract_ride_plan_summary(plan_data, monday)
            if ride_plan:
                if not isinstance(week_data, dict):
                    week_data = {}
                week_data["training_plan"] = ride_plan

            activities = (
                activities_data
                if isinstance(activities_data, list)
                else (activities_data or {}).get("activities")
            )

            coach_input = {
                "schema_version": _SCHEMA_VERSION,
                "week_starting": monday_str,
                "current_date": today.isoformat(),
                "metrics": metrics,
                "week_summary": week_data,
                "activities": activities,
                "fueling_analysis": fueling_data,
                "planned_workouts": planned_workouts_data,
            }

        # TemporaryDirectory context exited — both temp dirs are deleted automatically
        span.set_status(_OK)
        return json.dumps(coach_input, indent=2, ensure_ascii=False)


@mcp.tool()
def upload_week_plan(
    plan_json: str,
    dry_run: bool = False,
    clear: bool = False,
) -> str:
    """Upload a JSON training plan to intervals.icu as planned workout events.

    Writes the plan to a temporary file, calls upload_plan.py, then discards
    the file. Nothing is retained on the server after this call.

    Existing WORKOUT events with the same name and date are updated (PUT);
    new ones are created (POST) — no duplicates.

    Args:
        plan_json:  Training plan as a JSON string. Must be a JSON array of
                    workout objects or an object with a "workouts" array.
                    Each workout requires "date" (ISO 8601 datetime), "name",
                    and "duration_minutes".
                    Example:
                    [
                      {
                        "date": "2026-05-19T09:00:00",
                        "name": "Endurance Ride",
                        "duration_minutes": 90,
                        "description": "Zone 2 steady state",
                        "tags": ["endurance-moderate"]
                      }
                    ]
        dry_run:    If True, show what would be uploaded without making API calls.
        clear:      If True, delete all existing WORKOUT events for the plan's
                    date range before uploading (use to fix duplicates).
    """
    with _tool_span("mcp.tool/upload_week_plan") as span:
        span.set_attribute("dry_run", dry_run)
        span.set_attribute("clear", clear)

        err = _check_credentials()
        if err:
            span.set_status(_ERROR, "missing credentials")
            return err

        try:
            json.loads(plan_json)
        except json.JSONDecodeError as exc:
            span.set_status(_ERROR, f"invalid plan JSON: {exc}")
            return json.dumps({"error": f"Invalid JSON: {exc}"}, ensure_ascii=False)

        athlete_id, api_key = _get_credentials()
        env = os.environ.copy()
        env["INTERVALS_API_KEY"] = api_key
        env["ATHLETE_ID"] = athlete_id

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(plan_json)
            tmp_path = Path(tmp.name)

        try:
            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "upload_plan.py"),
                "--plan",
                str(tmp_path),
            ]
            if dry_run:
                cmd.append("--dry-run")
            if clear:
                cmd.append("--clear")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                stdin=subprocess.DEVNULL,
                env=env,
                check=False,
            )
            output = result.stdout + (
                f"\nSTDERR: {result.stderr}" if result.stderr.strip() else ""
            )
            if not output.strip():
                msg = "Done." if result.returncode == 0 else "Upload failed with no output."
                span.set_status(_OK if result.returncode == 0 else _ERROR, msg)
                return msg
            if result.returncode != 0:
                span.set_status(_ERROR, "upload script failed")
            else:
                span.set_status(_OK)
            return output.strip()
        except subprocess.TimeoutExpired:
            span.set_status(_ERROR, "upload timed out")
            return json.dumps({"error": "Upload timed out after 120s"}, ensure_ascii=False)
        finally:
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# ASGI app export (for uvicorn / App Service)
# ---------------------------------------------------------------------------

# CORSMiddleware is outermost so OPTIONS preflight requests (sent by the
# MCP Inspector and browsers) always get proper CORS headers, even for
# endpoints that don't exist (404).  Without this the Inspector shows
# "Error Connecting to MCP Inspector Proxy".
#
# Both transport endpoints are merged into one Starlette app:
#   /sse  /messages/  – SSE transport (legacy)
#   /mcp              – Streamable HTTP transport (modern)
_sse = mcp.sse_app()
_http = mcp.streamable_http_app()
_combined = Starlette(routes=list(_sse.routes) + list(_http.routes))

app = CORSMiddleware(
    AuthHeaderMiddleware(_combined),
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ---------------------------------------------------------------------------
# Entry point for local development
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("FASTMCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("FASTMCP_PORT", "8000")),
    )
