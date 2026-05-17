# intervals-icu-coach – Webservice

MCP server for Azure App Service. Exposes two tools over SSE transport, with credentials passed per-request via HTTP headers.

## Tools

| Tool | Description |
|---|---|
| `prepare_week_data` | Runs the full data pipeline (activities, metrics, training plan, fueling, week analysis) and returns the consolidated coach input as JSON. Nothing is stored on the server. |
| `upload_week_plan` | Uploads a JSON training plan to intervals.icu as planned workout events. Accepts `dry_run` and `clear` flags. |

## Authentication

Credentials are **not** stored on the server. Each MCP client connection must supply:

| Header | Value |
|---|---|
| `X-Intervals-Athlete-Id` | Your athlete ID (e.g. `i12345`) |
| `X-Intervals-Api-Key` | Your intervals.icu API key |

## Local development

```bash
# From the repo root, with the virtual environment active:

# Linux / macOS
MCP_TRANSPORT=sse INTERVALS_DEV_MODE=true python webservice/mcp_server.py

# Windows (PowerShell)
$env:MCP_TRANSPORT="sse"; $env:INTERVALS_DEV_MODE="true"; python webservice/mcp_server.py
```

The server listens on `http://localhost:8000/sse` by default.

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_HOST` | `0.0.0.0` | Bind address |
| `FASTMCP_PORT` | `8000` | Port |
| `FASTMCP_ALLOWED_HOST` | *(empty)* | Additional hostname for the `allowed_hosts` security check (e.g. the App Service hostname) |
| `INTERVALS_DEV_MODE` | *(empty)* | Set to `true` for local development: enables `/health` endpoint and falls back to `ATHLETE_ID` / `INTERVALS_API_KEY` from `.env` when credential headers are absent. **Never enable in production.** |

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Transport Type: **SSE**
2. URL: `http://localhost:8000/sse`
3. Connection Type: **Direct** (not "Via Proxy" – the proxy requires its own auth token that can expire)
4. Click **Connect**

The inspector connects directly to the server. CORS headers are served for all `localhost` origins, so no additional configuration is needed.

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

Copy `config.example.ps1` to `config.ps1` and fill in all values.
`config.ps1` is excluded from source control via `.gitignore` and must **never** be committed.

```powershell
cd webservice
Copy-Item config.example.ps1 config.ps1
# Edit config.ps1 with your actual values
.\setup.ps1 -All    # generates infra/main.local.bicepparam + pushes GitHub Secrets
```

### 5. Preview before deploying

```powershell
.\Check-Deployment.ps1
```

### 6. Deploy infrastructure

Push to `main` — the `infra.yml` workflow deploys automatically.
Or run manually:

```powershell
az deployment group create `
  --resource-group <your-resource-group> `
  --template-file infra/main.bicep `
  --parameters infra/main.local.bicepparam
```

### CI/CD Workflows

| Workflow | Trigger | Action |
|---|---|---|
| `infra.yml` | push to `main` (infra changes) + manual | Deploy Bicep infrastructure |
| `preview.yml` | PR to `main` (infra changes) | What-If → PR comment |
| `deploy.yml` | push to `main` | Zip-deploy code → **staging** slot |
| `deploy.yml` | PR to `main` | Zip-deploy code → **dev** slot |

Slot URLs follow the pattern `https://<appName>-<slot>.azurewebsites.net`.

### App Settings set by Bicep

| Setting | Value |
|---|---|
| `MCP_TRANSPORT` | `sse` |
| `FASTMCP_HOST` | `0.0.0.0` |
| `FASTMCP_PORT` | `8000` |
| `FASTMCP_ALLOWED_HOST` | `<appName>.azurewebsites.net` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

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
