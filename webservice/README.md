# intervals-icu-coach – Webservice

MCP server for Azure App Service. Exposes tools over SSE transport, with credentials passed per-request via HTTP headers.

## Tools

| Tool | Description |
|---|---|
| `prepare_week_data` | Runs the full data pipeline (activities, metrics, training plan, fueling, week analysis) and returns the consolidated coach input as JSON. Nothing is stored on the server. |
| `get_latest_activities` | Runs a slim pipeline and returns a compact, latest-first activity list (`date`, `name`, `duration_hours`, `training_load`, `avg_hr`, `max_hr`, `rpe`, `tags`) to avoid client-side truncation on large payloads. |
| `list_library_workouts` | Lists the authenticated caller's own workout library with key fields (`folder`, `name`, `duration`, `tss`, `tags`). Supports optional filters: `tag_prefixes`, `match_mode` (`any`/`all`), `include_untagged`, `limit`. |
| `list_standard_library_workouts` | Lists shared workouts of the configured standard library athlete (`STANDARD_LIBRARY_ATHLETE_ID`) with key fields (`shared_from`, `folder`, `name`, `duration`, `tss`, `tags`). Supports optional filters: `tag_prefixes`, `match_mode` (`any`/`all`), `include_untagged`, `limit`. |
| `upload_week_plan` | Uploads a JSON training plan to intervals.icu as planned workout events. Accepts `dry_run` and `clear` flags. |

## Authentication

The server supports three authentication methods, resolved in this priority order:

### 1. OAuth 2.0 (recommended for Claude.ai web)

The server implements a full OAuth 2.0 Authorization Server (RFC 6749) with PKCE (RFC 7636)
and Dynamic Client Registration (RFC 7591). Claude.ai and other OAuth-capable MCP clients
will discover the OAuth endpoints automatically via `/.well-known/oauth-authorization-server`
and open a browser login form where the user enters their Athlete ID and API Key.

The issued Bearer token is **stateless and Fernet-encrypted** — it contains the encrypted
credentials and an expiry timestamp. No token table is kept in memory; tokens survive
server restarts as long as `OAUTH_TOKEN_SECRET` stays the same.

Token lifetime: **30 days** by default. Configure with `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS`.

### 2. Custom headers (Claude Desktop / API clients)

| Header | Value |
|---|---|
| `X-Intervals-Athlete-Id` | Your athlete ID (e.g. `i12345`) |
| `X-Intervals-Api-Key` | Your intervals.icu API key |

### 3. URL path (Claude Desktop)

Credentials can be embedded directly in the URL path:
```
https://<host>/<athlete_id>/<api_key>/mcp
```

Credentials are **never stored** on the server.

## Local development

```bash
# From the repo root, with the virtual environment active:

# Linux / macOS
MCP_TRANSPORT=sse INTERVALS_DEV_MODE=true python webservice/mcp_server.py

# Windows (PowerShell)
$env:MCP_TRANSPORT="sse"; $env:INTERVALS_DEV_MODE="true"; python webservice/mcp_server.py
```

`MCP_TRANSPORT=sse` tells FastMCP to run in ASGI mode (instead of stdio).
**Both transports are always active with a single start command** — there is no separate mode for Streamable HTTP.
The server exposes two transport endpoints:

| Endpoint | Protocol | Notes |
|---|---|---|
| `http://localhost:8000/sse` | SSE (legacy) | `GET /sse` for stream, `POST /messages` for client→server |
| `http://localhost:8000/mcp` | Streamable HTTP (modern) | Single `POST /mcp` endpoint, bidirectional |

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_HOST` | `0.0.0.0` | Bind address |
| `FASTMCP_PORT` | `8000` | Port |
| `FASTMCP_ALLOWED_HOST` | *(empty)* | Additional hostname for the `allowed_hosts` security check (e.g. the App Service hostname) |
| `STANDARD_LIBRARY_ATHLETE_ID` | *(empty)* | Athlete ID used by MCP method `list_standard_library_workouts` to return shared standard-library workouts |
| `OAUTH_TOKEN_SECRET` | *(empty)* | Fernet key for stateless OAuth tokens. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. If not set, an ephemeral key is generated at startup and tokens are lost on restart. |
| `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` | `30` | Access-token lifetime in days. Increase this as a first mitigation when clients fail to refresh reliably. |
| `INTERVALS_DEV_MODE` | *(empty)* | Set to `true` for local development: falls back to `ATHLETE_ID` / `INTERVALS_API_KEY` from `.env` when no credentials are supplied. **Never enable in production.** |
| `MCP_TRACE_RESPONSE_JSON` | *(empty)* | Optional: set to `true` to include a truncated JSON response preview in traces/logs for `POST /mcp` responses. Default is off. |
| `MCP_TRACE_RESPONSE_PREVIEW_LIMIT` | `4096` | Maximum UTF-8 bytes captured as response preview when `MCP_TRACE_RESPONSE_JSON=true`. |
| `MCP_RPC_EVENT_LOG_LEVEL` | `INFO` | Log level for structured MCP RPC events (`INFO`, `WARNING`, `ERROR`). Keep `INFO` for semantic correctness; raise temporarily if your logging pipeline filters info traces. |

### Testing with MCP Inspector

`npx` is part of **Node.js** (included since npm v5.2). It must be installed on your machine —
download from [nodejs.org](https://nodejs.org) or run `winget install OpenJS.NodeJS`.
`npx` downloads and runs `@modelcontextprotocol/inspector` on demand without a permanent installation.

```bash
npx @modelcontextprotocol/inspector
```

**SSE transport (legacy):**
1. Transport Type: **SSE**
2. URL: `http://localhost:8000/sse`
3. Connection Type: **Direct**
4. Click **Connect**

**Streamable HTTP transport (modern):**
1. Transport Type: **Streamable HTTP**
2. URL: `http://localhost:8000/mcp`
3. Connection Type: **Direct**
4. Click **Connect**

CORS headers are served for all `localhost` origins, so no additional configuration is needed.

## Azure App Service deployment

### Prerequisites

- An existing App Service Plan (Linux)
- Azure CLI (`az`) or Azure Developer CLI (`azd`)

### 1. Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [GitHub CLI](https://cli.github.com/) (`winget install GitHub.cli`)
- Contributor role on the target resource group

### 2. Create Deployment Service Principal

Use `Create-ServicePrincipalForDeployment.ps1` from [cloud-admin-toolkit](https://github.com/brands-advisory/cloud-admin-toolkit):

```powershell
.\Create-ServicePrincipalForDeployment.ps1 -ConfigName intervals-icu-sync
```

### 3. Add OIDC Federated Credential

Use `Add-FederatedCredentialForGitHub.ps1` from [cloud-admin-toolkit](https://github.com/brands-advisory/cloud-admin-toolkit):

```powershell
.\Add-FederatedCredentialForGitHub.ps1 -ConfigName intervals-icu-sync
```

After this step no client secret is stored anywhere. OIDC handles authentication via GitHub's identity provider.

### 4. Local Configuration

The deployment config is project-wide and lives in the **repo root**. Copy
`config.example.ps1` to `config.ps1` (root) and fill in all values. `config.ps1`
is excluded from source control via `.gitignore` and must **never** be committed.

| Key in `config.ps1` | GitHub Secret | Description |
|---|---|---|
| `SubscriptionId` | `AZURE_SUBSCRIPTION_ID` | Azure subscription GUID |
| `TenantId` | `AZURE_TENANT_ID` | Entra ID tenant GUID |
| `AzureClientId` | `AZURE_CLIENT_ID` | Service principal client ID |
| `ResourceGroup` | `AZURE_RESOURCE_GROUP` | Target resource group |
| `Location` | `AZURE_LOCATION` | Azure region |
| `AppName` | `APP_NAME` | App Service name (globally unique) |
| `AppServicePlanName` | `APP_SERVICE_PLAN_NAME` | Existing App Service Plan name |
| `AppInsightsName` | `APP_INSIGHTS_NAME` | Existing Application Insights instance name |
| `CustomDomain` | `APP_CUSTOM_DOMAIN` | Optional custom domain (e.g. `intervals-mcp.training-architect.com`). Leave empty to use only the `.azurewebsites.net` hostname. |
| `OAuthTokenSecret` | `OAUTH_TOKEN_SECRET` | Fernet key for stateless OAuth tokens. Generate once and store permanently. See `OAUTH_TOKEN_SECRET` above. |
| `OAuthAccessTokenLifetimeDays` | `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` | Access-token lifetime in days (default `30`). Useful workaround when a client's refresh flow is unreliable. |
| `StandardLibraryAthleteId` | `STANDARD_LIBRARY_ATHLETE_ID` | Athlete ID whose shared library is exposed by MCP method `list_standard_library_workouts` (e.g. `i57401`). |
| `McpTraceResponseJson` | `MCP_TRACE_RESPONSE_JSON` | Controls MCP response preview tracing (`true`/`false`). Recommended: `false` in normal production operation. |
| `McpTraceResponsePreviewLimit` | `MCP_TRACE_RESPONSE_PREVIEW_LIMIT` | Max UTF-8 bytes captured as response preview when tracing is enabled (e.g. `4096`). |
| `McpRpcEventLogLevel` | `MCP_RPC_EVENT_LOG_LEVEL` | Log level for structured MCP RPC events (`INFO`, `WARNING`, `ERROR`). Recommended default: `INFO`. |
| `FoundryProjectEndpoint` | `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint used by the "Deploy Foundry Agent" workflow (`foundry-agent/deploy_agent.py`), e.g. `https://<resource>.services.ai.azure.com/api/projects/<project>`. |
| `FoundryResourceGroup` | `FOUNDRY_RESOURCE_GROUP` | Resource group for the Foundry infrastructure (separate from the webservice RG). Used by the "Deploy Foundry Infrastructure" workflow. |
| `FoundryAccountName` | `FOUNDRY_ACCOUNT_NAME` | Foundry (AI Services) account name (e.g. `training-architect`). |
| `FoundryProjectName` | `FOUNDRY_PROJECT_NAME` | Foundry project name (e.g. `training-architect`). |
| `FoundryLocation` | `FOUNDRY_LOCATION` | Region for the Foundry resources (e.g. `swedencentral`). |
| `FoundryModelVersion` | `FOUNDRY_MODEL_VERSION` | Model version for the `gpt-4.1-mini` deployment. |
| `FoundryDeployPrincipalId` | `FOUNDRY_DEPLOY_PRINCIPAL_ID` | Object id of the deployment service principal granted data-plane access. |

```powershell
# From the repo root
Copy-Item config.example.ps1 config.ps1
# Edit config.ps1 with your actual values
.\setup.ps1 -All    # generates both infra/main.local.bicepparam files + pushes GitHub Secrets
```

### 5. Preview and deploy infrastructure

`Check-Deployment.ps1` stays in `webservice/` and reads `config.ps1` from the
repo root. Run `setup.ps1 -Bicep` (from root) first, then:

```powershell
cd webservice
.\Check-Deployment.ps1           # lint + what-if only
.\Check-Deployment.ps1 -Deploy   # lint + what-if + deploy (with confirmation prompt)
```

### 6. Deploy infrastructure (first-time bootstrap)

Because `infra.yml` only appears in the GitHub Actions UI after it has been merged to `main`,
the very first deployment must be done **locally**:

```powershell
cd webservice
.\Check-Deployment.ps1 -Deploy   # lint + what-if + deploy (with confirmation)
```

> After the PR is merged, `infra.yml` is available in the GitHub Actions UI under
> **Actions → Deploy Infrastructure → Run workflow**. It must always be triggered
> **manually** — it never runs automatically on push.

### 7. Deploy code (first time)

After the infrastructure exists, trigger the code deploy manually:

```powershell
gh workflow run deploy.yml --ref feature/<your-branch>
```

Or, once on `main`, via **Actions → Deploy Code → Run workflow** (target slot: `staging`).

From the second PR onwards `deploy.yml` and `preview.yml` run automatically; `infra.yml` and `swap.yml` are always manual.

### CI/CD Workflows

| Workflow | Trigger | Action |
|---|---|---|
| `infra.yml` | manual (`workflow_dispatch` only) | Deploy Bicep infrastructure |
| `preview.yml` | PR to `main` (only if infra files changed in push) | What-If → PR comment |
| `deploy.yml` | push to `main` | Zip-deploy code → **staging** slot |
| `deploy.yml` | PR to `main` | Zip-deploy code → **dev** slot |
| `swap.yml` | manual (`workflow_dispatch` only) | Health check staging → swap staging → production → health check production |

Slot URLs follow the pattern `https://<appName>-<slot>.azurewebsites.net`.

#### Typical development workflow

1. **Create a feature branch** — `git checkout -b feature/<short-title>`
2. **Open a PR** against `main`
   - `deploy.yml` deploys the code to the **dev** slot automatically
   - `preview.yml` runs a Bicep What-If and posts the result as a PR comment (only if infra files changed)
   - Test at `https://<appName>-dev.azurewebsites.net`
3. **Merge the PR** — `deploy.yml` deploys the code to the **staging** slot automatically
   - Test at `https://<appName>-staging.azurewebsites.net`
4. **Infrastructure changes** (Bicep) — always trigger `infra.yml` manually via
   **Actions → Deploy Infrastructure → Run workflow** before or after merging
5. **Go live** — trigger `swap.yml` manually via **Actions → Swap Slots → Run workflow**
   - Health-checks staging, swaps staging ↔ production, health-checks production

### Transport endpoints

Both transports share the same tools, middleware, and Application Insights instrumentation:

On script/tool failures, the MCP server now emits structured error log entries
with event marker `mcp_tool_error` (including `tool`, `error_type`, `script`,
`return_code`, `host`, and `slot`) so failures are visible in Application
Insights even when callers only see a generic error.

For `POST /mcp` requests, the server also extracts JSON-RPC metadata and writes
it into traces so you can see what was called inside a generic MCP endpoint:

- request-span attributes: `mcp.rpc.method`, `mcp.tool.name` (for `tools/call`), `mcp.request.id`
- internal span name: `mcp.rpc/<method>`
- structured trace event: `mcp_rpc_request`

For `POST /mcp` responses, the server writes response metadata to traces/logs:

- always: `mcp.response.status_code`, `mcp.response.body_size`, `mcp.response.sha256`
- optional (feature flag): `mcp.response.preview` and structured event `mcp_rpc_response.response_preview`
- structured trace event: `mcp_rpc_response`

Recommendation: keep `MCP_TRACE_RESPONSE_JSON` disabled in production unless you
actively debug a payload issue, because response previews can contain sensitive
athlete data and increase telemetry volume.

| Endpoint | Protocol | Use case |
|---|---|---|
| `/sse` + `/messages` | SSE | MCP Inspector, older clients |
| `/mcp` | Streamable HTTP | Modern MCP clients, Claude Desktop |

### App Settings set by Bicep

| Setting | Value |
|---|---|
| `MCP_TRANSPORT` | `sse` |
| `FASTMCP_HOST` | `0.0.0.0` |
| `FASTMCP_PORT` | `8000` |
| `FASTMCP_ALLOWED_HOST` | `<appName>.azurewebsites.net` (slot-sticky) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Connection string of the existing Application Insights instance |
| `OAUTH_TOKEN_SECRET` | Fernet key for stateless OAuth tokens (from GitHub Secret `OAUTH_TOKEN_SECRET`) |
| `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` | Access-token lifetime in days (default `30`) |
| `STANDARD_LIBRARY_ATHLETE_ID` | Athlete ID for MCP method `list_standard_library_workouts` (from GitHub Secret `STANDARD_LIBRARY_ATHLETE_ID`) |
| `MCP_TRACE_RESPONSE_JSON` | `false` (recommended) or `true` for temporary payload debugging |
| `MCP_TRACE_RESPONSE_PREVIEW_LIMIT` | `4096` |
| `MCP_RPC_EVENT_LOG_LEVEL` | `INFO` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `ENABLE_ORYX_BUILD` | `true` |

The startup command configured in Bicep:

```
python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000
```

### Health check

The `/health` endpoint is always available (no authentication required):

```
GET https://<appName>.azurewebsites.net/health
```

Response:
```json
{"status": "ok", "schema_version": "1.2.3", "dev_mode": false, "timestamp": "2026-05-17T..."}
```

This can be configured as the **Health check path** in the App Service settings (`/health`).

## Directory layout

```
webservice/
├── context.py          # ContextVar definitions for per-request credentials
├── mcp_server.py       # FastMCP server – tools + ASGI middleware
├── requirements.txt    # Python dependencies (subset of root, + uvicorn)
├── README.md           # This file
└── infra/
    ├── main.bicep               # Orchestration
    ├── main.local.bicepparam    # Local parameters (gitignored; generated by setup.ps1)
    └── modules/
        └── appservice.bicep     # Web App resource (references existing plan)
```
