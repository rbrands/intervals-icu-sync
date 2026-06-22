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
import json
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

try:
    import azure.data.tables as azure_tables  # type: ignore[import-not-found]
    import azure.core.exceptions as azure_exceptions  # type: ignore[import-not-found]
    from azure.identity import DefaultAzureCredential  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for local dev
    azure_tables = None
    azure_exceptions = None
    DefaultAzureCredential = None
    ResourceExistsError = RuntimeError
    AzureError = RuntimeError
else:
    ResourceExistsError = azure_exceptions.ResourceExistsError
    AzureError = azure_exceptions.AzureError

_TABLE_STORAGE_ERRORS = (AzureError,)


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


class _OAuthClientStore:
    """Persist OAuth client registrations in Azure Table Storage.

    Uses Managed Identity / DefaultAzureCredential and gracefully degrades when
    table storage is not configured or unavailable.
    """

    _PARTITION_KEY = "oauth_client"

    def __init__(self, table_client: Any) -> None:
        self._table_client = table_client

    @classmethod
    def from_environment(cls) -> "_OAuthClientStore | None":
        account_name = os.environ.get("OAUTH_CLIENT_STORAGE_ACCOUNT", "").strip()
        table_name = os.environ.get("OAUTH_CLIENT_TABLE_NAME", "mcpoauthclients").strip()

        if not account_name:
            logger.info(
                "OAuth client persistence disabled (OAUTH_CLIENT_STORAGE_ACCOUNT not set)."
            )
            return None

        if azure_tables is None or DefaultAzureCredential is None:
            logger.warning(
                "OAuth client persistence requested but Azure Table dependencies are missing. "
                "Install azure-data-tables and azure-identity to enable persistence."
            )
            return None

        endpoint = f"https://{account_name}.table.core.windows.net"
        try:
            credential = DefaultAzureCredential()
            service_client = azure_tables.TableServiceClient(endpoint=endpoint, credential=credential)
            table_client = service_client.get_table_client(table_name=table_name)
            try:
                table_client.create_table()
                logger.info(
                    "Created OAuth client registry table '%s' in storage account '%s'.",
                    table_name,
                    account_name,
                )
            except ResourceExistsError:
                pass
            logger.info(
                "OAuth client persistence enabled using table '%s' in storage account '%s'.",
                table_name,
                account_name,
            )
            return cls(table_client)
        except _TABLE_STORAGE_ERRORS as exc:
            logger.exception(
                "Failed to initialize OAuth client table storage (%s/%s): %s. "
                "Falling back to in-memory registrations.",
                account_name,
                table_name,
                exc,
            )
            return None

    def save_client(self, client: _Client) -> None:
        self.cleanup_expired_clients()
        now_iso = datetime.now(timezone.utc).isoformat()
        entity = {
            "PartitionKey": self._PARTITION_KEY,
            "RowKey": client.client_id,
            "client_name": client.client_name,
            "client_secret": client.client_secret or "",
            "token_endpoint_auth_method": client.token_endpoint_auth_method,
            "redirect_uris_json": json.dumps(client.redirect_uris),
            "updated_at_utc": now_iso,
            "created_at_utc": now_iso,
        }

        try:
            existing = self._table_client.get_entity(
                partition_key=self._PARTITION_KEY,
                row_key=client.client_id,
            )
            created_at = existing.get("created_at_utc")
            if isinstance(created_at, str) and created_at:
                entity["created_at_utc"] = created_at
        except _TABLE_STORAGE_ERRORS:
            # Entity does not exist or could not be fetched; upsert handles both.
            pass

        self._table_client.upsert_entity(entity=entity, mode="replace")

    def cleanup_expired_clients(self, max_age_days: int = 200) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed = 0

        try:
            entities: list[dict[str, Any]] = list(self._table_client.query_entities(
                query_filter=f"PartitionKey eq '{self._PARTITION_KEY}'"
            ))
        except _TABLE_STORAGE_ERRORS:
            return 0

        for entity in entities:
            created_at_raw = entity.get("created_at_utc")
            if not isinstance(created_at_raw, str) or not created_at_raw:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                continue

            if created_at >= cutoff:
                continue

            row_key = entity.get("RowKey")
            if not isinstance(row_key, str) or not row_key:
                continue

            try:
                self._table_client.delete_entity(
                    partition_key=self._PARTITION_KEY,
                    row_key=row_key,
                )
                removed += 1
            except _TABLE_STORAGE_ERRORS:
                continue

        if removed:
            logger.info(
                "Removed %s expired OAuth client registrations older than %s days.",
                removed,
                max_age_days,
            )
        return removed

    def load_client(self, client_id: str) -> _Client | None:
        try:
            entity = self._table_client.get_entity(
                partition_key=self._PARTITION_KEY,
                row_key=client_id,
            )
        except _TABLE_STORAGE_ERRORS:
            return None

        redirect_uris_raw = entity.get("redirect_uris_json") or "[]"
        try:
            redirect_uris = json.loads(redirect_uris_raw)
            if not isinstance(redirect_uris, list):
                redirect_uris = []
        except (TypeError, ValueError):
            redirect_uris = []

        client_secret = entity.get("client_secret") or None
        client_name = str(entity.get("client_name") or "unknown")
        auth_method = str(entity.get("token_endpoint_auth_method") or "client_secret_post")

        return _Client(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=[str(uri) for uri in redirect_uris],
            client_name=client_name,
            token_endpoint_auth_method=auth_method,
        )


def _base_url_from_request(request: Request) -> str:
    """Derive the public base URL from request headers (works behind App Service / Cloudflare)."""
    host = request.headers.get("host", "localhost:8000")
    # Azure App Service and Cloudflare set X-Forwarded-Proto
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}"


class IntervalsOAuthProvider:
    """Self-contained OAuth 2.0 Authorization Server for intervals.icu credentials.

    Authorization/pending/token state is stateless (Fernet-encrypted tokens). Dynamic client registrations
    are persisted to Azure Table Storage when configured, otherwise they remain
    in-memory. Create a single instance and register its routes on the Starlette
    app. Pass the instance to AuthHeaderMiddleware so it can resolve Bearer
    tokens to (athlete_id, api_key) pairs.
    """

    _DEFAULT_TOKEN_LIFETIME_DAYS = 30
    _REFRESH_TOKEN_LIFETIME = timedelta(days=365)
    _CODE_LIFETIME = timedelta(minutes=10)
    _PENDING_LIFETIME = timedelta(minutes=30)

    def __init__(self) -> None:
        self._token_lifetime = timedelta(days=self._parse_positive_int_env(
            "OAUTH_ACCESS_TOKEN_LIFETIME_DAYS",
            self._DEFAULT_TOKEN_LIFETIME_DAYS,
        ))

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
        self._client_store = _OAuthClientStore.from_environment()

    def _get_client(self, client_id: str) -> _Client | None:
        client = self._clients.get(client_id)
        if client is not None:
            return client

        if self._client_store is None:
            return None

        try:
            stored = self._client_store.load_client(client_id)
        except _TABLE_STORAGE_ERRORS as exc:
            logger.warning("Failed to load OAuth client '%s' from table storage: %s", client_id, exc)
            return None

        if stored is not None:
            self._clients[client_id] = stored
        return stored

    def _save_client(self, client: _Client) -> None:
        self._clients[client.client_id] = client
        if self._client_store is None:
            return

        try:
            self._client_store.save_client(client)
        except _TABLE_STORAGE_ERRORS as exc:
            logger.warning(
                "Failed to persist OAuth client '%s' to table storage: %s",
                client.client_id,
                exc,
            )

    @staticmethod
    def _parse_positive_int_env(name: str, default: int) -> int:
        """Parse a positive integer env var with safe fallback."""
        raw = os.environ.get(name)
        if not raw:
            return default

        try:
            parsed = int(raw)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            pass

        logger.warning(
            "%s=%r is invalid; falling back to %s.",
            name,
            raw,
            default,
        )
        return default

    # ------------------------------------------------------------------
    # Public API used by AuthHeaderMiddleware
    # ------------------------------------------------------------------

    def get_credentials(self, bearer_token: str) -> tuple[str, str] | None:
        """Return (athlete_id, api_key) for a valid Bearer token, or None."""
        try:
            plaintext = self._fernet.decrypt(bearer_token.encode()).decode()
        except (InvalidToken, ValueError):
            return None
        # Reject refresh tokens used as access tokens
        if plaintext.startswith("refresh:"):
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
                "grant_types_supported": ["authorization_code", "refresh_token"],
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
        self._save_client(client)

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

        client = self._get_client(client_id)
        if client is None:
            return Response("Unknown client_id.", status_code=400)

        if redirect_uri and client.redirect_uris and redirect_uri not in client.redirect_uris:
            return Response("redirect_uri mismatch.", status_code=400)

        # Encode pending state as a Fernet-encrypted token so any App Service
        # instance can validate it without shared in-memory state.
        pending_payload = json.dumps({
            "client_id": client_id,
            "redirect_uri": redirect_uri or (client.redirect_uris[0] if client.redirect_uris else ""),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "expires_at": (datetime.now(timezone.utc) + self._PENDING_LIFETIME).isoformat(),
        })
        req_id = self._fernet.encrypt(pending_payload.encode()).decode()
        base = _base_url_from_request(request)
        return RedirectResponse(f"{base}/oauth/form?req_id={req_id}", status_code=302)

    # ------------------------------------------------------------------
    # Login form
    # ------------------------------------------------------------------

    def _decode_pending(self, req_id: str) -> _PendingAuth | None:
        """Decode a Fernet-encrypted pending-auth token. Returns None if invalid or expired."""
        try:
            data = json.loads(self._fernet.decrypt(req_id.encode()).decode())
            expires_at = datetime.fromisoformat(data["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return None
            return _PendingAuth(
                client_id=data["client_id"],
                redirect_uri=data["redirect_uri"],
                state=data.get("state"),
                code_challenge=data.get("code_challenge"),
                code_challenge_method=data.get("code_challenge_method", "S256"),
            )
        except (InvalidToken, ValueError, KeyError):
            return None

    async def _handle_form(self, request: Request) -> Response:
        if request.method == "GET":
            req_id = request.query_params.get("req_id", "")
            if self._decode_pending(req_id) is None:
                return Response("Invalid or expired request.", status_code=400)
            return HTMLResponse(_login_html(req_id))

        # POST – process submitted credentials
        form = await request.form()
        req_id = str(form.get("req_id", ""))
        athlete_id = str(form.get("athlete_id", "")).strip()
        api_key = str(form.get("api_key", "")).strip()

        pending = self._decode_pending(req_id)
        if pending is None:
            return Response("Invalid or expired request.", status_code=400)
        if not athlete_id or not api_key:
            return HTMLResponse(
                _login_html(req_id, error="Please enter both Athlete ID and API Key."),
                status_code=422,
            )

        # Encode auth code as a Fernet-encrypted token so any App Service
        # instance can validate it at the token endpoint without shared state.
        code_payload = json.dumps({
            "athlete_id": athlete_id,
            "api_key": api_key,
            "client_id": pending.client_id,
            "redirect_uri": pending.redirect_uri,
            "code_challenge": pending.code_challenge,
            "code_challenge_method": pending.code_challenge_method,
            "expires_at": (datetime.now(timezone.utc) + self._CODE_LIFETIME).isoformat(),
        })
        code = self._fernet.encrypt(code_payload.encode()).decode()

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

        if grant_type == "refresh_token":
            return await self._handle_refresh_token(request, form)

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

        client = self._get_client(client_id)
        if client is None:
            return JSONResponse({"error": "invalid_client"}, status_code=401)

        # Validate secret (skip for public clients)
        if client.client_secret is not None:
            if not hmac.compare_digest(
                client_secret_provided, client.client_secret
            ):
                return JSONResponse({"error": "invalid_client"}, status_code=401)

        # Validate authorization code (Fernet-encrypted, stateless)
        code = str(form.get("code", ""))
        try:
            code_data = json.loads(self._fernet.decrypt(code.encode()).decode())
            code_expires_at = datetime.fromisoformat(code_data["expires_at"])
        except (InvalidToken, ValueError, KeyError):
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid or expired code"},
                status_code=401,
            )
        if code_expires_at < datetime.now(timezone.utc):
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Code expired"},
                status_code=401,
            )
        if code_data.get("client_id") != client_id:
            return JSONResponse({"error": "invalid_grant"}, status_code=401)

        # PKCE verification (S256)
        code_challenge = code_data.get("code_challenge")
        if code_challenge:
            code_verifier = str(form.get("code_verifier", ""))
            if not code_verifier:
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "code_verifier required"},
                    status_code=401,
                )
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            if not hmac.compare_digest(computed, code_challenge):
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                    status_code=401,
                )

        athlete_id_val = code_data["athlete_id"]
        api_key_val = code_data["api_key"]

        # Issue access token (Fernet-encrypted, stateless)
        expires_at = datetime.now(timezone.utc) + self._token_lifetime
        payload = f"{athlete_id_val}:{api_key_val}:{expires_at.isoformat()}"
        token_str = self._fernet.encrypt(payload.encode()).decode()
        expires_in = int(self._token_lifetime.total_seconds())

        # Issue refresh token (long-lived, Fernet-encrypted, stateless)
        refresh_expires_at = datetime.now(timezone.utc) + self._REFRESH_TOKEN_LIFETIME
        refresh_payload = f"refresh:{athlete_id_val}:{api_key_val}:{refresh_expires_at.isoformat()}"
        refresh_token_str = self._fernet.encrypt(refresh_payload.encode()).decode()

        return JSONResponse(
            {
                "access_token": token_str,
                "token_type": "bearer",
                "expires_in": expires_in,
                "refresh_token": refresh_token_str,
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    async def _handle_refresh_token(self, _request: Request, form) -> JSONResponse:
        """Handle grant_type=refresh_token: validate refresh token and issue new access token."""
        refresh_token = str(form.get("refresh_token", ""))
        if not refresh_token:
            return JSONResponse({"error": "invalid_request", "error_description": "refresh_token required"}, status_code=400)

        try:
            plaintext = self._fernet.decrypt(refresh_token.encode()).decode()
        except (InvalidToken, ValueError):
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid refresh token"}, status_code=401)

        if not plaintext.startswith("refresh:"):
            return JSONResponse({"error": "invalid_grant", "error_description": "Not a refresh token"}, status_code=401)

        parts = plaintext[len("refresh:"):].split(":", 2)
        if len(parts) != 3:
            return JSONResponse({"error": "invalid_grant"}, status_code=401)

        athlete_id, api_key, expires_str = parts
        try:
            expires_at = datetime.fromisoformat(expires_str)
        except ValueError:
            return JSONResponse({"error": "invalid_grant"}, status_code=401)

        if expires_at < datetime.now(timezone.utc):
            return JSONResponse({"error": "invalid_grant", "error_description": "Refresh token expired"}, status_code=401)

        # Issue new access token
        new_expires_at = datetime.now(timezone.utc) + self._token_lifetime
        payload = f"{athlete_id}:{api_key}:{new_expires_at.isoformat()}"
        token_str = self._fernet.encrypt(payload.encode()).decode()
        expires_in = int(self._token_lifetime.total_seconds())

        # Issue a new (rotated) refresh token with a fresh expiry window.
        # As long as the client refreshes at least once per year, re-authentication
        # is never required.
        new_refresh_expires_at = datetime.now(timezone.utc) + self._REFRESH_TOKEN_LIFETIME
        new_refresh_payload = f"refresh:{athlete_id}:{api_key}:{new_refresh_expires_at.isoformat()}"
        new_refresh_token_str = self._fernet.encrypt(new_refresh_payload.encode()).decode()

        return JSONResponse(
            {
                "access_token": token_str,
                "token_type": "bearer",
                "expires_in": expires_in,
                "refresh_token": new_refresh_token_str,  # Rotated: fresh 1-year expiry
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
