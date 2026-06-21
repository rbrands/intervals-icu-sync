"""MCP server for Azure App Service deployment.

Exposes MCP tools over SSE transport:
    - prepare_week_data       – runs the full data pipeline and returns the
                                                            consolidated coach input as JSON
    - get_latest_activities   – returns a compact list of latest rides
    - list_library_workouts   – lists the caller's own workout library entries
    - list_standard_library_workouts – lists shared workouts of configured standard library athlete
    - upload_week_plan        – uploads a JSON training plan to intervals.icu

Credentials are resolved in priority order:
  1. URL path   /{athlete_id}/{api_key}/mcp  or  /{athlete_id}/{api_key}/sse
  2. Headers    X-Intervals-Athlete-Id  /  X-Intervals-Api-Key
  3. OAuth 2.0  Authorization: Bearer <token>  (issued after the login form flow)

OAuth 2.0 endpoints (for Claude.ai and other OAuth-capable MCP clients):
  GET  /.well-known/oauth-protected-resource   – resource metadata (RFC 9728)
  GET  /.well-known/oauth-authorization-server – authorization server metadata
  POST /register                               – dynamic client registration
  GET  /authorize                              – start authorization code flow
  GET  /oauth/form                             – credentials entry form
  POST /oauth/form                             – form submit → auth code
  POST /token                                  – exchange code for Bearer token

MCP endpoints return 401 + WWW-Authenticate when no credentials are supplied,
which lets OAuth-capable clients discover and start the OAuth flow automatically.

Run locally (SSE mode):
    # Linux / macOS:
    MCP_TRANSPORT=sse python webservice/mcp_server.py
    # Windows (PowerShell):
    $env:MCP_TRANSPORT="sse"; python webservice/mcp_server.py

App Service startup command:
    python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000
"""

import json
import logging
import os
import re
import hashlib
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
    _otel_trace = None
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
from intervals_icu.client import get_library_folders, get_library_workouts

from context import api_key_var, athlete_id_var
from intervals_icu.prompt_templates import render_coach_prompt
from oauth_provider import IntervalsOAuthProvider

# Singleton OAuth provider – shared between the ASGI app and the auth middleware.
_oauth = IntervalsOAuthProvider()

_VERSION_FILE = _ROOT / "VERSION"
_SCHEMA_VERSION = (
    _VERSION_FILE.read_text(encoding="utf-8").strip()
    if _VERSION_FILE.exists()
    else "unknown"
)

_logger = logging.getLogger("intervals_icu_mcp")
_MCP_TRACE_BODY_LIMIT = 64 * 1024
_MCP_RPC_EVENT_LOG_LEVEL = os.environ.get("MCP_RPC_EVENT_LOG_LEVEL", "INFO").strip().upper()
_MCP_TRACE_RESPONSE_ENABLED = os.environ.get("MCP_TRACE_RESPONSE_JSON", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_MCP_TRACE_RESPONSE_PREVIEW_LIMIT = int(
    os.environ.get("MCP_TRACE_RESPONSE_PREVIEW_LIMIT", "4096")
)


def _log_mcp_rpc_event(payload: dict) -> None:
    """Log MCP RPC structured events with configurable severity (default INFO)."""
    level = _MCP_RPC_EVENT_LOG_LEVEL
    if level == "WARNING":
        _logger.warning(json.dumps(payload, ensure_ascii=False))
        return
    if level == "ERROR":
        _logger.error(json.dumps(payload, ensure_ascii=False))
        return
    _logger.info(json.dumps(payload, ensure_ascii=False))


def _slot_name() -> str:
    return os.environ.get("WEBSITE_SLOT_NAME", "production")


def _emit_tool_error(
    tool_name: str,
    error_type: str,
    message: str,
    **context,
) -> None:
    """Emit structured error logs that are easy to query in Application Insights."""
    payload = {
        "event": "mcp_tool_error",
        "tool": tool_name,
        "error_type": error_type,
        "message": message,
        "schema_version": _SCHEMA_VERSION,
        "host": os.environ.get("WEBSITE_HOSTNAME", "local"),
        "slot": _slot_name(),
    }
    payload.update(context)
    _logger.error(json.dumps(payload, ensure_ascii=False))


def _extract_mcp_rpc_metadata(body: bytes) -> tuple[str, str | None, str | None]:
    """Return (jsonrpc_method, tool_name, request_id) from a POST /mcp body."""
    if not body:
        return "unknown", None, None

    try:
        decoded = body.decode("utf-8", errors="replace")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid-json", None, None

    request_obj = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(request_obj, dict):
        return "unknown", None, None

    method = str(request_obj.get("method") or "unknown")
    params = request_obj.get("params")
    tool_name = None
    if method == "tools/call" and isinstance(params, dict):
        name = params.get("name")
        if isinstance(name, str) and name:
            tool_name = name

    request_id = request_obj.get("id")
    request_id_str = str(request_id) if request_id is not None else None
    return method, tool_name, request_id_str


def _trace_mcp_request(path: str, body: bytes) -> None:
    """Attach MCP RPC metadata to the current request span and emit an internal span."""
    method, tool_name, request_id = _extract_mcp_rpc_metadata(body)

    if _otel_trace is not None:
        current_span = _otel_trace.get_current_span()
        if current_span is not None:
            current_span.set_attribute("mcp.rpc.method", method)
            if tool_name:
                current_span.set_attribute("mcp.tool.name", tool_name)
            if request_id:
                current_span.set_attribute("mcp.request.id", request_id)

    span_name = f"mcp.rpc/{method}"
    with _tool_span(span_name) as span:
        span.set_attribute("mcp.path", path)
        span.set_attribute("mcp.rpc.method", method)
        if tool_name:
            span.set_attribute("mcp.tool.name", tool_name)
        if request_id:
            span.set_attribute("mcp.request.id", request_id)
        span.set_status(_OK)

    _log_mcp_rpc_event(
        {
            "event": "mcp_rpc_request",
            "path": path,
            "rpc_method": method,
            "tool": tool_name,
            "request_id": request_id,
            "schema_version": _SCHEMA_VERSION,
            "host": os.environ.get("WEBSITE_HOSTNAME", "local"),
            "slot": _slot_name(),
        }
    )


def _trace_mcp_response(path: str, status_code: int | None, body: bytes) -> None:
    """Attach MCP response metadata and optional JSON preview to traces/logs."""
    body_size = len(body)
    body_sha256 = hashlib.sha256(body).hexdigest() if body else None
    preview_bytes = body[: max(0, _MCP_TRACE_RESPONSE_PREVIEW_LIMIT)]
    preview_text = preview_bytes.decode("utf-8", errors="replace") if preview_bytes else ""

    if _otel_trace is not None:
        current_span = _otel_trace.get_current_span()
        if current_span is not None:
            if status_code is not None:
                current_span.set_attribute("mcp.response.status_code", status_code)
            current_span.set_attribute("mcp.response.body_size", body_size)
            if body_sha256:
                current_span.set_attribute("mcp.response.sha256", body_sha256)
            if _MCP_TRACE_RESPONSE_ENABLED and preview_text:
                current_span.set_attribute("mcp.response.preview", preview_text)

    span_name = "mcp.rpc/response"
    with _tool_span(span_name) as span:
        span.set_attribute("mcp.path", path)
        if status_code is not None:
            span.set_attribute("mcp.response.status_code", status_code)
        span.set_attribute("mcp.response.body_size", body_size)
        if body_sha256:
            span.set_attribute("mcp.response.sha256", body_sha256)
        if _MCP_TRACE_RESPONSE_ENABLED and preview_text:
            span.set_attribute("mcp.response.preview", preview_text)
        span.set_status(_OK)

    payload = {
        "event": "mcp_rpc_response",
        "path": path,
        "status_code": status_code,
        "response_size": body_size,
        "response_sha256": body_sha256,
        "response_preview_truncated": body_size > len(preview_bytes),
        "schema_version": _SCHEMA_VERSION,
        "host": os.environ.get("WEBSITE_HOSTNAME", "local"),
        "slot": _slot_name(),
    }
    if _MCP_TRACE_RESPONSE_ENABLED and preview_text:
        payload["response_preview"] = preview_text

    _log_mcp_rpc_event(payload)

# allowed_hosts: always include localhost variants (with and without port) plus
# any hostnames listed in FASTMCP_ALLOWED_HOST (comma-separated, e.g.
# "myapp.azurewebsites.net,intervals-mcp.training-architect.com").
# The Host header sent by clients includes the port (e.g. "localhost:8000"), so
# both forms must be listed.
_extra_hosts: list[str] = [
    h.strip()
    for h in os.environ.get("FASTMCP_ALLOWED_HOST", "").split(",")
    if h.strip()
]
_port = int(os.environ.get("FASTMCP_PORT", "8000"))
_allowed_hosts: list[str] = [
    "127.0.0.1",
    "localhost",
    f"127.0.0.1:{_port}",
    f"localhost:{_port}",
]
_allowed_hosts.extend(_extra_hosts)

# allowed_origins: localhost:* covers any port (MCP Inspector, VS Code, etc.).
# Localhost origins can only come from the local machine, so this is safe in
# all environments. The wildcard "http://localhost:*" is supported by the SDK's
# _validate_origin() method.
_allowed_origins: list[str] = ["http://localhost:*", "https://localhost:*"]
for _h in _extra_hosts:
    _allowed_origins.append(f"https://{_h}")

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
_STANDARD_LIBRARY_ATHLETE_ID: str = os.environ.get("STANDARD_LIBRARY_ATHLETE_ID", "").strip()

# Matches URL-embedded credentials: /{athlete_id}/{api_key}/{mcp|sse|messages...}
# Allows clients that cannot set custom headers to pass credentials via the path.
# The negative lookahead (?!\.) excludes dot-prefixed segments (e.g. .well-known)
# so that OAuth discovery paths are never misinterpreted as URL-embedded credentials.
_URL_AUTH_RE = re.compile(r"^/(?!\.)([^/]+)/([^/]+)(/(?:mcp|sse|messages).*)$")


# MCP protocol endpoints that require authentication.
_MCP_PATHS = ("/mcp", "/sse", "/messages")


class AuthHeaderMiddleware:
    """Resolves credentials from (in priority order):

    1. URL-embedded path  ``/{athlete_id}/{api_key}/{mcp|sse|messages…}``
    2. Custom request headers  ``X-Intervals-Athlete-Id`` / ``X-Intervals-Api-Key``
    3. OAuth 2.0 Bearer token  ``Authorization: Bearer <token>``
    4. Dev-mode env-var fallback (``INTERVALS_DEV_MODE=true`` only)

    Implemented as a pure ASGI middleware so SSE streams are never buffered.

    Public routes (health, OAuth discovery, login form, token endpoint) are
    forwarded unconditionally.  MCP endpoints (``/mcp``, ``/sse``, ``/messages``)
    return ``401 Unauthorized`` with a ``WWW-Authenticate`` header when no
    credentials can be resolved, so that OAuth-capable clients can start the
    OAuth 2.0 Authorization Code flow automatically.
    """

    def __init__(self, asgi_app) -> None:
        self._asgi_app = asgi_app

    async def __call__(self, scope, receive, send) -> None:
        traced_receive = receive
        traced_send = send

        if scope["type"] == "http":
            path = scope.get("path", "")
            # Root path – serve a landing page for humans; Azure App Service
            # health pings also hit "/" but accept any 2xx.
            if path == "/":
                await self._handle_landing(scope, receive, send)
                return
            # Health endpoints (also handles /sse/health and /mcp/health for MCP Inspector)
            if path in ("/health", "/sse/health", "/mcp/health"):
                await self._handle_health(scope, receive, send)
                return
            # Config probe used by MCP Inspector – return a minimal discovery doc
            if path == "/sse/config":
                await self._handle_sse_config(scope, receive, send)
                return

            # Capture JSON-RPC metadata for Streamable HTTP MCP calls.
            # Also supports URL-embedded credentials:
            #   /{athlete_id}/{api_key}/mcp
            trace_path = path
            url_trace_match = _URL_AUTH_RE.match(path)
            if url_trace_match:
                trace_path = url_trace_match.group(3)

            if trace_path.startswith("/mcp"):
                captured: list[bytes] = []
                captured_size = 0
                parsed = False
                response_captured: list[bytes] = []
                response_size = 0
                response_status_code: int | None = None
                response_parsed = False

                async def _receive_with_mcp_trace():
                    nonlocal captured_size, parsed
                    message = await receive()
                    if message.get("type") == "http.request":
                        chunk = message.get("body", b"")
                        if isinstance(chunk, bytes) and chunk and captured_size < _MCP_TRACE_BODY_LIMIT:
                            remaining = _MCP_TRACE_BODY_LIMIT - captured_size
                            captured.append(chunk[:remaining])
                            captured_size += min(len(chunk), remaining)

                        if not message.get("more_body", False) and not parsed:
                            parsed = True
                            _trace_mcp_request(trace_path, b"".join(captured))
                    return message

                traced_receive = _receive_with_mcp_trace

                async def _send_with_mcp_trace(message):
                    nonlocal response_size, response_status_code, response_parsed

                    if message.get("type") == "http.response.start":
                        status = message.get("status")
                        if isinstance(status, int):
                            response_status_code = status

                    if message.get("type") == "http.response.body":
                        chunk = message.get("body", b"")
                        was_empty = response_size == 0
                        if isinstance(chunk, bytes) and chunk and response_size < _MCP_TRACE_BODY_LIMIT:
                            remaining = _MCP_TRACE_BODY_LIMIT - response_size
                            response_captured.append(chunk[:remaining])
                            response_size += min(len(chunk), remaining)

                        # MCP Streamable HTTP keeps the SSE stream open after sending the
                        # tool result, so more_body=False never arrives during normal operation.
                        # Trace on the first data chunk (SSE event with the result) as well as
                        # on stream end (plain JSON responses or graceful close).
                        if not response_parsed and (
                            not message.get("more_body", False)
                            or (was_empty and response_size > 0)
                        ):
                            response_parsed = True
                            _trace_mcp_response(trace_path, response_status_code, b"".join(response_captured))

                    await send(message)

                traced_send = _send_with_mcp_trace

        if scope["type"] in ("http", "websocket"):
            header_dict = {k.lower(): v for k, v in scope.get("headers", [])}
            athlete_id = ""
            api_key = ""

            # 1) URL-embedded credentials: /{athlete_id}/{api_key}/{mcp|sse|messages…}
            url_match = _URL_AUTH_RE.match(scope.get("path", ""))
            if url_match:
                athlete_id = url_match.group(1)
                api_key = url_match.group(2)
                inner_path = url_match.group(3)
                scope = {**scope, "path": inner_path, "raw_path": inner_path.encode()}

            # 2) Custom request headers
            if not (athlete_id and api_key):
                athlete_id = header_dict.get(
                    b"x-intervals-athlete-id", b""
                ).decode("utf-8", errors="replace")
                api_key = header_dict.get(
                    b"x-intervals-api-key", b""
                ).decode("utf-8", errors="replace")

            # 3) OAuth 2.0 Bearer token
            if not (athlete_id and api_key):
                auth_val = header_dict.get(b"authorization", b"").decode(
                    "utf-8", errors="replace"
                )
                if auth_val.lower().startswith("bearer "):
                    bearer = auth_val[7:].strip()
                    creds = _oauth.get_credentials(bearer)
                    if creds:
                        athlete_id, api_key = creds

            # 4) Dev-mode env-var fallback
            if _DEV_MODE and not (athlete_id and api_key):
                athlete_id = athlete_id or os.environ.get("ATHLETE_ID", "")
                api_key = api_key or os.environ.get("INTERVALS_API_KEY", "")

            # Return 401 for MCP endpoints when credentials are still missing.
            # The WWW-Authenticate header tells OAuth-capable clients where to
            # discover the authorization server (RFC 9728 / MCP spec).
            if not (athlete_id and api_key) and scope["type"] == "http":
                current_path = scope.get("path", "")
                if any(current_path.startswith(p) for p in _MCP_PATHS):
                    await self._handle_401(scope, receive, send, header_dict)
                    return

            token_a = athlete_id_var.set(athlete_id)
            token_k = api_key_var.set(api_key)
            try:
                await self._asgi_app(scope, traced_receive, traced_send)
            finally:
                athlete_id_var.reset(token_a)
                api_key_var.reset(token_k)
        else:
            await self._asgi_app(scope, traced_receive, traced_send)

    @staticmethod
    async def _handle_401(scope, receive, send, header_dict: dict) -> None:  # noqa: ARG004
        """Return 401 with a WWW-Authenticate header for unauthenticated MCP requests."""
        # Derive the public base URL from the Host header so the resource
        # metadata URL is correct regardless of which hostname the client used.
        host = header_dict.get(b"host", b"localhost").decode("utf-8", errors="replace")
        # X-Forwarded-Proto is set by App Service / Cloudflare
        proto = header_dict.get(b"x-forwarded-proto", b"http").decode("utf-8", errors="replace")
        base = f"{proto}://{host}"
        resource_meta_url = f"{base}/.well-known/oauth-protected-resource"
        www_auth = f'Bearer resource_metadata="{resource_meta_url}"'
        body = b'{"error":"unauthorized","error_description":"Authentication required."}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
                [b"www-authenticate", www_auth.encode()],
                [b"access-control-allow-origin", b"*"],
            ],
        })
        await send({"type": "http.response.body", "body": body})

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
    async def _handle_landing(scope, receive, send) -> None:  # noqa: ARG004
        """Return a human-readable landing page for the MCP server."""
        header_dict = {k.lower(): v for k, v in scope.get("headers", [])}
        host = header_dict.get(b"host", b"localhost").decode("utf-8", errors="replace")
        proto = header_dict.get(b"x-forwarded-proto", b"http").decode("utf-8", errors="replace")
        base = f"{proto}://{host}"
        body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>intervals-icu-sync MCP Server</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 4rem auto; padding: 0 1.5rem; color: #222; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    p.sub {{ color: #666; margin-top: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1.5rem 0; }}
    th, td {{ text-align: left; padding: 0.5rem 0.75rem; border: 1px solid #ddd; }}
    th {{ background: #f5f5f5; }}
    code {{ background: #f0f0f0; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.9em; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>intervals-icu-sync</h1>
  <p class="sub">MCP Server — cycling training data from <a href="https://intervals.icu">intervals.icu</a> &nbsp;|&nbsp; Version {_SCHEMA_VERSION}</p>
  <p class="sub">See <a href="https://github.com/rbrands/intervals-icu-sync">GitHub repository intervals-icu-sync</a> for details including step-by-step guides how 
    to set up and use the MCP server in popular GenAI platforms.</p>
  <h2>Endpoints</h2>
  <table>
    <tr><th>URL</th><th>Protocol</th></tr>
    <tr><td><code>{base}/mcp</code></td><td>Streamable HTTP (modern)</td></tr>
    <tr><td><code>{base}/sse</code></td><td>SSE (legacy)</td></tr>
  </table>
    <h2>MCP Methods</h2>
    <table>
        <tr><th>Method</th><th>Description</th></tr>
        <tr><td><code>prepare_week_data</code></td><td>Runs the full weekly pipeline and returns consolidated coach input JSON.</td></tr>
        <tr><td><code>get_latest_activities</code></td><td>Returns a compact latest-first activity list to avoid large payload truncation.</td></tr>
        <tr><td><code>list_library_workouts</code></td><td>Lists the caller's own workout library with duration, TSS and tags. Supports optional filters: tag_prefixes, match_mode (any/all), include_untagged, limit.</td></tr>
        <tr><td><code>list_standard_library_workouts</code></td><td>Lists shared workouts of STANDARD_LIBRARY_ATHLETE_ID with duration, TSS and tags. Supports optional filters: tag_prefixes, match_mode (any/all), include_untagged, limit.</td></tr>
        <tr><td><code>upload_week_plan</code></td><td>Uploads a JSON training plan to intervals.icu (supports dry-run and clear).</td></tr>
    </table>
  <h2>Authentication</h2>
  <table>
    <tr><th>Method</th><th>How</th></tr>
    <tr><td>OAuth 2.0</td><td>Login via browser — automatic for Claude.ai</td></tr>
    <tr><td>Custom headers</td><td><code>X-Intervals-Athlete-Id</code> + <code>X-Intervals-Api-Key</code></td></tr>
    <tr><td>URL path</td><td><code>{base}/&lt;athlete_id&gt;/&lt;api_key&gt;/mcp</code></td></tr>
  </table>
  <p><a href="{base}/health">Health check</a></p>
</body>
</html>""".encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [[b"content-type", b"text/html; charset=utf-8"],
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
) -> tuple[bool, str, int | None]:
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
        return False, f"Timeout after {timeout}s", None
    output = result.stdout + (
        f"\nSTDERR: {result.stderr}" if result.stderr.strip() else ""
    )
    return result.returncode == 0, output.strip(), result.returncode


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

    def _build(
        targets_key: str,
        constraints_key: str,
        week_monday: date,
        phase_list: list,
    ) -> dict | None:
        targets = [
            t for t in (plan_data.get(targets_key) or [])
            if t.get("sport_type") == "Ride"
        ]
        week_constraints = plan_data.get(constraints_key) or []
        if not phase_list and not targets and not week_constraints:
            return None
        entry: dict = {"week": week_monday.isoformat()}
        if phase_list:
            p = phase_list[0]
            entry.update({k: p.get(k) for k in ("plan_name", "phase", "start", "end")})
        if targets:
            t = targets[0]
            entry["weekly_load_target"] = t.get("load_target")
            entry["week_type"] = t.get("week_type", "NORMAL")
            if t.get("week_note"):
                entry["week_note"] = t["week_note"]
        if week_constraints:
            entry["day_constraints"] = week_constraints
        return entry

    result: list[dict] = []
    current = _build("weekly_load_targets", "weekly_day_constraints", monday, phases)
    if current:
        result.append(current)
    nxt = _build(
        "next_week_load_targets",
        "next_week_day_constraints",
        monday + timedelta(weeks=1),
        next_phases or phases,
    )
    if nxt:
        result.append(nxt)
    return result


def _format_duration(seconds: int | float | None) -> str:
    total_seconds = int(seconds or 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


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
                ok, output, return_code = _run_script(script, extra_env=extra_env)
                status = "OK" if ok else "FAILED"
                log_lines.append(f"[{status}] {script}")
                if output:
                    log_lines.append(f"       {output[:300]}")
                if not ok:
                    _emit_tool_error(
                        "prepare_week_data",
                        "pipeline_step_failed",
                        f"Pipeline failed at {script}",
                        script=script,
                        return_code=return_code,
                        details=output[:2000],
                    )
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
def get_latest_activities(limit: int = 10) -> str:
    """Return a compact, latest-first list of activities for the current week.

    This tool is intended for MCP clients that may truncate very large tool
    outputs. It runs a slim pipeline and returns only core fields, including
    heart-rate summary values when available.

    Args:
        limit: Maximum number of activities to return (1-100, default 10).
    """
    with _tool_span("mcp.tool/get_latest_activities") as span:
        span.set_attribute("limit", limit)

        err = _check_credentials()
        if err:
            span.set_status(_ERROR, "missing credentials")
            return err

        if limit < 1 or limit > 100:
            span.set_status(_ERROR, "invalid limit")
            return json.dumps(
                {"error": "limit must be between 1 and 100"},
                ensure_ascii=False,
            )

        pipeline = [
            "get_activities.py",
            "prepare_activities_for_coach.py",
        ]

        with tempfile.TemporaryDirectory(prefix="intervals_raw_") as tmp_raw, \
             tempfile.TemporaryDirectory(prefix="intervals_proc_") as tmp_proc:

            tmp_raw_path = Path(tmp_raw)
            tmp_proc_path = Path(tmp_proc)
            extra_env = {
                "INTERVALS_RAW_DIR": str(tmp_raw_path),
                "INTERVALS_PROCESSED_DIR": str(tmp_proc_path),
            }

            for script in pipeline:
                ok, output, return_code = _run_script(script, extra_env=extra_env)
                if not ok:
                    _emit_tool_error(
                        "get_latest_activities",
                        "pipeline_step_failed",
                        f"Pipeline failed at {script}",
                        script=script,
                        return_code=return_code,
                        details=output[:2000],
                    )
                    span.set_status(_ERROR, f"pipeline failed at {script}")
                    return json.dumps(
                        {
                            "error": f"Pipeline failed at {script}",
                            "details": output[:500],
                        },
                        ensure_ascii=False,
                    )

            monday_str = _current_monday().isoformat()
            activities_data = _load_json_file(tmp_proc_path / f"coach_input_{monday_str}.json")
            activities = (
                activities_data
                if isinstance(activities_data, list)
                else (activities_data or {}).get("activities")
            )

            if not isinstance(activities, list):
                _emit_tool_error(
                    "get_latest_activities",
                    "no_activities_generated",
                    "No activities generated for current week.",
                )
                span.set_status(_ERROR, "no activities")
                return json.dumps(
                    {"error": "No activities generated for current week."},
                    ensure_ascii=False,
                )

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

        span.set_status(_OK)
        return json.dumps(
            {
                "schema_version": _SCHEMA_VERSION,
                "week_starting": _current_monday().isoformat(),
                "current_date": date.today().isoformat(),
                "total_activities": len(activities),
                "returned": len(compact),
                "activities": compact,
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool()
def list_library_workouts(
    tag_prefixes: list[str] | str | None = None,
    match_mode: str = "any",
    include_untagged: bool = False,
    limit: int = 500,
) -> str:
    """List own workout library entries for the authenticated caller.

    Returns folder, name, duration, TSS and tags for each workout.

    Args:
        tag_prefixes: Optional tag prefix filter (e.g. ["aerobic-threshold-", "lactate-threshold-"]).
        match_mode: "any" (default) or "all" when multiple prefixes are provided.
        include_untagged: Include workouts without tags when tag_prefixes is set.
        limit: Maximum number of rows to return (1-5000).
    """
    with _tool_span("mcp.tool/list_library_workouts") as span:
        span.set_attribute("match_mode", match_mode)
        span.set_attribute("include_untagged", include_untagged)
        span.set_attribute("limit", limit)

        err = _check_credentials()
        if err:
            span.set_status(_ERROR, "missing credentials")
            return err

        if match_mode not in {"any", "all"}:
            span.set_status(_ERROR, "invalid match_mode")
            return json.dumps({"error": "match_mode must be 'any' or 'all'"}, ensure_ascii=False)
        if limit < 1 or limit > 5000:
            span.set_status(_ERROR, "invalid limit")
            return json.dumps({"error": "limit must be between 1 and 5000"}, ensure_ascii=False)

        athlete_id, api_key = _get_credentials()
        folders = get_library_folders(api_key, athlete_id)
        workouts = get_library_workouts(api_key, athlete_id)
        folder_map = _flatten_folders(folders)
        normalized = _normalize_library_workouts(workouts, folder_map)
        filtered, normalized_prefixes = _apply_workout_filters(
            normalized,
            tag_prefixes,
            match_mode,
            include_untagged,
            limit,
        )

        span.set_status(_OK)
        return json.dumps(
            {
                "schema_version": _SCHEMA_VERSION,
                "athlete_id": athlete_id,
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
    """List shared workouts of the configured standard library athlete.

    Uses env var STANDARD_LIBRARY_ATHLETE_ID as source athlete id.

    Args:
        tag_prefixes: Optional tag prefix filter (e.g. ["aerobic-threshold-", "lactate-threshold-"]).
        match_mode: "any" (default) or "all" when multiple prefixes are provided.
        include_untagged: Include workouts without tags when tag_prefixes is set.
        limit: Maximum number of rows to return (1-5000).
    """
    with _tool_span("mcp.tool/list_standard_library_workouts") as span:
        span.set_attribute("match_mode", match_mode)
        span.set_attribute("include_untagged", include_untagged)
        span.set_attribute("limit", limit)

        err = _check_credentials()
        if err:
            span.set_status(_ERROR, "missing credentials")
            return err

        if match_mode not in {"any", "all"}:
            span.set_status(_ERROR, "invalid match_mode")
            return json.dumps({"error": "match_mode must be 'any' or 'all'"}, ensure_ascii=False)
        if limit < 1 or limit > 5000:
            span.set_status(_ERROR, "invalid limit")
            return json.dumps({"error": "limit must be between 1 and 5000"}, ensure_ascii=False)

        if not _STANDARD_LIBRARY_ATHLETE_ID:
            span.set_status(_ERROR, "missing standard library athlete id")
            return json.dumps(
                {
                    "error": "STANDARD_LIBRARY_ATHLETE_ID is not configured on the server.",
                },
                ensure_ascii=False,
            )

        _, api_key = _get_credentials()
        folders = get_library_folders(api_key, _STANDARD_LIBRARY_ATHLETE_ID)
        rows = _collect_shared_outgoing_workouts(folders, _STANDARD_LIBRARY_ATHLETE_ID)
        rows.sort(key=lambda row: (row["shared_from"], row["folder"], row["name"].lower()))
        filtered, normalized_prefixes = _apply_workout_filters(
            rows,
            tag_prefixes,
            match_mode,
            include_untagged,
            limit,
        )

        span.set_status(_OK)
        return json.dumps(
            {
                "schema_version": _SCHEMA_VERSION,
                "standard_library_athlete_id": _STANDARD_LIBRARY_ATHLETE_ID,
                "total_workouts": len(rows),
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
            _emit_tool_error(
                "upload_week_plan",
                "invalid_json",
                f"Invalid JSON: {exc}",
            )
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
                if result.returncode != 0:
                    _emit_tool_error(
                        "upload_week_plan",
                        "upload_failed_no_output",
                        msg,
                        return_code=result.returncode,
                    )
                span.set_status(_OK if result.returncode == 0 else _ERROR, msg)
                return msg
            if result.returncode != 0:
                _emit_tool_error(
                    "upload_week_plan",
                    "upload_script_failed",
                    "upload_plan.py returned non-zero",
                    return_code=result.returncode,
                    details=output[:2000],
                )
                span.set_status(_ERROR, "upload script failed")
            else:
                span.set_status(_OK)
            return output.strip()
        except subprocess.TimeoutExpired:
            _emit_tool_error(
                "upload_week_plan",
                "upload_timeout",
                "Upload timed out after 120s",
            )
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
#
# streamable_http_app() lazily creates mcp._session_manager. Its Starlette app
# passes `lifespan=lambda app: self.session_manager.run()` internally; that
# lifespan is lost when we extract routes only. We therefore carry it over
# explicitly so the StreamableHTTPSessionManager's task group is initialised
# before any /mcp request arrives.
_sse = mcp.sse_app()
_http = mcp.streamable_http_app()  # initialises mcp._session_manager
_combined = Starlette(
    routes=_oauth.get_routes() + list(_sse.routes) + list(_http.routes),
    lifespan=lambda app: mcp.session_manager.run(),
)

# configure_azure_monitor() auto-instruments FastAPI/Flask/Django but not plain
# Starlette. Instrument explicitly so that HTTP request spans are captured.
try:
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor
    StarletteInstrumentor().instrument_app(_combined)
except ImportError:
    pass

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
