"""Minimal OAuth 2.0 Authorization Server for the intervals.icu MCP server.

Allows Claude.ai (and other OAuth-capable MCP clients) to authenticate by
entering their intervals.icu Athlete ID and API Key through a browser form.

OAuth 2.0 endpoints served:
  GET  /.well-known/oauth-protected-resource   – RFC 9728 resource metadata
  GET  /.well-known/oauth-authorization-server – RFC 8414 server metadata
  POST /register                               – Dynamic client registration (RFC 7591)
  GET  /authorize                              – Redirect to login form
  GET  /oauth/form                             – Login form (HTML)
  POST /oauth/form                             – Submit credentials → auth code
  POST /token                                  – Exchange code for Bearer token

Tokens are Fernet-encrypted and stateless: they embed athlete_id, api_key, and
expiry. No token table is kept in memory, so tokens survive server restarts as
long as the OAUTH_TOKEN_SECRET environment variable stays the same.

If OAUTH_TOKEN_SECRET is not set, a random key is generated at startup (tokens
will be invalidated on restart – acceptable for local development).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route


@dataclass
class _Client:
    client_id: str
    client_secret: str | None
    redirect_uris: list[str]
    client_name: str
    token_endpoint_auth_method: str = "client_secret_post"


@dataclass
class _PendingAuth:
    client_id: str
    redirect_uri: str
    state: str | None
    code_challenge: str | None
    code_challenge_method: str


@dataclass
class _AuthCode:
    code: str
    athlete_id: str
    api_key: str
    client_id: str
    redirect_uri: str
    code_challenge: str | None
    code_challenge_method: str
    expires_at: datetime


def _base_url_from_request(request: Request) -> str:
    """Derive the public base URL from request headers (works behind App Service / Cloudflare)."""
    host = request.headers.get("host", "localhost:8000")
    # Azure App Service and Cloudflare set X-Forwarded-Proto
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}"


class IntervalsOAuthProvider:
    """Self-contained OAuth 2.0 Authorization Server for intervals.icu credentials.

    All state is in-memory. Create a single instance and register its routes
    on the Starlette app.  Pass the instance to AuthHeaderMiddleware so it can
    resolve Bearer tokens to (athlete_id, api_key) pairs.
    """

    _TOKEN_LIFETIME = timedelta(days=30)
    _CODE_LIFETIME = timedelta(minutes=10)
    _PENDING_LIFETIME = timedelta(minutes=30)

    def __init__(self) -> None:
        raw_key = os.environ.get("OAUTH_TOKEN_SECRET")
        if raw_key:
            self._fernet = Fernet(raw_key.encode())
        else:
            generated = Fernet.generate_key()
            self._fernet = Fernet(generated)
            logger.warning(
                "OAUTH_TOKEN_SECRET not set – generated ephemeral key. "
                "Tokens will be invalidated on restart."
            )
        self._clients: dict[str, _Client] = {}
        self._pending: dict[str, _PendingAuth] = {}
        self._codes: dict[str, _AuthCode] = {}

    # ------------------------------------------------------------------
    # Public API used by AuthHeaderMiddleware
    # ------------------------------------------------------------------

    def get_credentials(self, bearer_token: str) -> tuple[str, str] | None:
        """Return (athlete_id, api_key) for a valid Bearer token, or None."""
        try:
            plaintext = self._fernet.decrypt(bearer_token.encode()).decode()
        except (InvalidToken, ValueError):
            return None
        parts = plaintext.split(":", 2)
        if len(parts) != 3:
            return None
        athlete_id, api_key, expires_str = parts
        try:
            expires_at = datetime.fromisoformat(expires_str)
        except ValueError:
            return None
        if expires_at < datetime.now(timezone.utc):
            return None
        return athlete_id, api_key

    def get_routes(self) -> list[Route]:
        """Return Starlette routes to be prepended to the combined app."""
        return [
            Route(
                "/.well-known/oauth-protected-resource",
                endpoint=self._handle_protected_resource,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-protected-resource/{path:path}",
                endpoint=self._handle_protected_resource,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-authorization-server",
                endpoint=self._handle_auth_server_meta,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-authorization-server/{path:path}",
                endpoint=self._handle_auth_server_meta,
                methods=["GET"],
            ),
            Route("/register", endpoint=self._handle_register, methods=["POST"]),
            Route("/authorize", endpoint=self._handle_authorize, methods=["GET"]),
            Route(
                "/oauth/form",
                endpoint=self._handle_form,
                methods=["GET", "POST"],
            ),
            Route("/token", endpoint=self._handle_token, methods=["POST"]),
        ]

    # ------------------------------------------------------------------
    # OAuth discovery endpoints
    # ------------------------------------------------------------------

    async def _handle_protected_resource(self, request: Request) -> JSONResponse:
        base = _base_url_from_request(request)
        return JSONResponse(
            {
                "resource": f"{base}/mcp",
                "authorization_servers": [base],
                "bearer_methods_supported": ["header"],
            },
            headers={"Access-Control-Allow-Origin": "*"},
        )

    async def _handle_auth_server_meta(self, request: Request) -> JSONResponse:
        base = _base_url_from_request(request)
        return JSONResponse(
            {
                "issuer": base,
                "authorization_endpoint": f"{base}/authorize",
                "token_endpoint": f"{base}/token",
                "registration_endpoint": f"{base}/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": [
                    "client_secret_post",
                    "client_secret_basic",
                    "none",
                ],
            },
            headers={"Access-Control-Allow-Origin": "*"},
        )

    # ------------------------------------------------------------------
    # Dynamic Client Registration (RFC 7591)
    # ------------------------------------------------------------------

    async def _handle_register(self, request: Request) -> JSONResponse:
        try:
            body: dict[str, Any] = await request.json()
        except (ValueError, KeyError):
            return JSONResponse({"error": "invalid_request"}, status_code=400)

        client_id = secrets.token_urlsafe(16)
        auth_method = body.get("token_endpoint_auth_method", "client_secret_post")
        client_secret = (
            None if auth_method == "none" else secrets.token_urlsafe(32)
        )
        redirect_uris: list[str] = body.get("redirect_uris") or []
        client = _Client(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            client_name=body.get("client_name", "unknown"),
            token_endpoint_auth_method=auth_method,
        )
        self._clients[client_id] = client

        response_body: dict[str, Any] = {
            "client_id": client_id,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": auth_method,
        }
        if client_secret:
            response_body["client_secret"] = client_secret
        return JSONResponse(response_body, status_code=201)

    # ------------------------------------------------------------------
    # Authorization endpoint
    # ------------------------------------------------------------------

    async def _handle_authorize(self, request: Request) -> Response:
        client_id = request.query_params.get("client_id", "")
        redirect_uri = request.query_params.get("redirect_uri", "")
        state = request.query_params.get("state")
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get(
            "code_challenge_method", "S256"
        )
        response_type = request.query_params.get("response_type", "code")

        if response_type != "code":
            return JSONResponse(
                {"error": "unsupported_response_type"}, status_code=400
            )

        client = self._clients.get(client_id)
        if client is None:
            return Response("Unknown client_id.", status_code=400)

        if redirect_uri and client.redirect_uris and redirect_uri not in client.redirect_uris:
            return Response("redirect_uri mismatch.", status_code=400)

        req_id = secrets.token_urlsafe(16)
        self._pending[req_id] = _PendingAuth(
            client_id=client_id,
            redirect_uri=redirect_uri or (client.redirect_uris[0] if client.redirect_uris else ""),
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        base = _base_url_from_request(request)
        return RedirectResponse(f"{base}/oauth/form?req_id={req_id}", status_code=302)

    # ------------------------------------------------------------------
    # Login form
    # ------------------------------------------------------------------

    async def _handle_form(self, request: Request) -> Response:
        if request.method == "GET":
            req_id = request.query_params.get("req_id", "")
            if req_id not in self._pending:
                return Response("Invalid or expired request.", status_code=400)
            return HTMLResponse(_login_html(req_id))

        # POST – process submitted credentials
        form = await request.form()
        req_id = str(form.get("req_id", ""))
        athlete_id = str(form.get("athlete_id", "")).strip()
        api_key = str(form.get("api_key", "")).strip()

        pending = self._pending.pop(req_id, None)
        if pending is None:
            return Response("Invalid or expired request.", status_code=400)
        if not athlete_id or not api_key:
            # Put the pending record back so the user can retry
            self._pending[req_id] = pending
            return HTMLResponse(
                _login_html(req_id, error="Please enter both Athlete ID and API Key."),
                status_code=422,
            )

        code = secrets.token_urlsafe(32)
        self._codes[code] = _AuthCode(
            code=code,
            athlete_id=athlete_id,
            api_key=api_key,
            client_id=pending.client_id,
            redirect_uri=pending.redirect_uri,
            code_challenge=pending.code_challenge,
            code_challenge_method=pending.code_challenge_method,
            expires_at=datetime.now(timezone.utc) + self._CODE_LIFETIME,
        )

        redirect = f"{pending.redirect_uri}?code={code}"
        if pending.state:
            redirect += f"&state={pending.state}"
        return RedirectResponse(redirect, status_code=302)

    # ------------------------------------------------------------------
    # Token endpoint
    # ------------------------------------------------------------------

    async def _handle_token(self, request: Request) -> JSONResponse:
        form = await request.form()
        grant_type = str(form.get("grant_type", ""))

        if grant_type != "authorization_code":
            return JSONResponse(
                {"error": "unsupported_grant_type"}, status_code=400
            )

        # Client authentication: client_secret_post or client_secret_basic
        client_id = str(form.get("client_id", ""))
        client_secret_provided = str(form.get("client_secret", ""))

        if not client_id:
            # Try Authorization header (Basic auth)
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("basic "):
                try:
                    decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                    client_id, _, client_secret_provided = decoded.partition(":")
                except (ValueError, UnicodeDecodeError):
                    pass

        client = self._clients.get(client_id)
        if client is None:
            return JSONResponse({"error": "invalid_client"}, status_code=401)

        # Validate secret (skip for public clients)
        if client.client_secret is not None:
            if not hmac.compare_digest(
                client_secret_provided, client.client_secret
            ):
                return JSONResponse({"error": "invalid_client"}, status_code=401)

        # Validate authorization code
        code = str(form.get("code", ""))
        auth_code = self._codes.pop(code, None)
        if auth_code is None:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid or expired code"},
                status_code=401,
            )
        if auth_code.client_id != client_id:
            return JSONResponse({"error": "invalid_grant"}, status_code=401)
        if auth_code.expires_at < datetime.now(timezone.utc):
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Code expired"},
                status_code=401,
            )

        # PKCE verification (S256)
        if auth_code.code_challenge:
            code_verifier = str(form.get("code_verifier", ""))
            if not code_verifier:
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "code_verifier required"},
                    status_code=401,
                )
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            if not hmac.compare_digest(computed, auth_code.code_challenge):
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                    status_code=401,
                )

        # Issue access token (Fernet-encrypted, stateless)
        expires_at = datetime.now(timezone.utc) + self._TOKEN_LIFETIME
        payload = f"{auth_code.athlete_id}:{auth_code.api_key}:{expires_at.isoformat()}"
        token_str = self._fernet.encrypt(payload.encode()).decode()
        expires_in = int(self._TOKEN_LIFETIME.total_seconds())

        return JSONResponse(
            {
                "access_token": token_str,
                "token_type": "bearer",
                "expires_in": expires_in,
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )


# ---------------------------------------------------------------------------
# HTML login form
# ---------------------------------------------------------------------------

def _login_html(req_id: str, error: str = "") -> str:
    error_block = (
        f'<p class="error">{error}</p>' if error else ""
    )
    # req_id is a cryptographically random token – safe to embed in HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>intervals.icu – Connect to AI Coach</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #f0f4f8;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 1rem;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,.08);
      padding: 2rem;
      max-width: 420px;
      width: 100%;
    }}
    h1 {{ font-size: 1.35rem; color: #1d3557; margin: 0 0 .5rem; }}
    p.lead {{ color: #555; margin: 0 0 1.5rem; font-size: .95rem; }}
    label {{ display: block; font-size: .875rem; color: #333; margin-top: 1rem; }}
    input {{
      width: 100%; padding: .6rem .8rem; border: 1px solid #ccd;
      border-radius: 6px; margin-top: .3rem; font-size: 1rem;
    }}
    input:focus {{ outline: 2px solid #457b9d; border-color: transparent; }}
    .hint {{ font-size: .75rem; color: #777; margin-top: .25rem; }}
    button {{
      margin-top: 1.5rem; width: 100%; padding: .75rem;
      background: #1d3557; color: #fff; border: none;
      border-radius: 6px; font-size: 1rem; cursor: pointer;
    }}
    button:hover {{ background: #457b9d; }}
    .error {{ color: #c0392b; font-size: .875rem; margin-top: .75rem; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Connect intervals.icu to AI Coach</h1>
    <p class="lead">
      Enter your intervals.icu credentials so the AI coach can read your
      training data.  Your credentials are never stored on this server.
    </p>
    {error_block}
    <form method="POST" action="/oauth/form">
      <input type="hidden" name="req_id" value="{req_id}">
      <label>
        Athlete ID
        <input name="athlete_id" placeholder="e.g. i12345" required autocomplete="username">
        <span class="hint">Found in your intervals.icu profile URL</span>
      </label>
      <label>
        API Key
        <input type="password" name="api_key" placeholder="Your intervals.icu API key" required autocomplete="current-password">
        <span class="hint">Settings → Developer → API Key in intervals.icu</span>
      </label>
      <button type="submit">Connect</button>
    </form>
  </div>
</body>
</html>"""
