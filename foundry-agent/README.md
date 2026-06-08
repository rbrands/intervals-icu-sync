# Foundry Agent — training-architect-agent

Version-controlled definition of the Microsoft Foundry prompt agent that coaches
based on intervals.icu data (via MCP) and the `coach-logic/` knowledge base.

## Files

- `agent.yaml` — declarative agent definition (model, instructions, tools).

## Instructions and discipline (runtime structured input)

`agent.yaml` embeds **all** discipline profiles and selects one at runtime via a
[structured input](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/structured-inputs)
called `discipline` (a Handlebars `{{discipline}}` placeholder). One agent
version serves every discipline — no per-discipline versions needed.

The response language is also runtime-controlled with `response_language`
(`{{response_language}}` in the prompt), so the same agent version can answer
in different languages per request.

At deploy time, `deploy_agent.py` replaces the `<<INSERT DISCIPLINE PROFILES HERE>>`
placeholder with the four discipline blocks:

| Discipline value | Source file |
| ---------------- | ----------- |
| `climber` | `../prompts/discipline_climber.md` |
| `criterium` | `../prompts/discipline_criterium.md` |
| `marathon` | `../prompts/discipline_marathon.md` |
| `roadrace` | `../prompts/discipline_roadrace.md` |

The `structured_inputs.discipline` schema in `agent.yaml` defaults to `climber`,
and `response_language` defaults to `de`, so the agent works without supplying
values. To select discipline and language per request, pass both via
`structured_inputs`:

```python
project_client = AIProjectClient(endpoint=project_endpoint, credential=credential, allow_preview=True)
openai_client = project_client.get_openai_client(agent_name="training-architect-agent")

response = openai_client.responses.create(
    input="Plan my next week",
    extra_body={
      "structured_inputs": {
        "discipline": "marathon",
        "response_language": "en",
      },
    },
)
```

> **Note:** Handlebars here supports `if`/`unless`/`each` but not an equality
> helper, so the profiles are embedded and the agent applies the one matching
> `{{discipline}}`. Users can also just state their discipline in chat.

## Knowledge (file_search vector store)

The `file_search` tool uses a vector store built from the `coach-logic/` files:

- `coaching-principles.md`
- `interpretation-rules.md`
- `decision-process.md`
- `training-zones.md`
- `input-schema.md`
- `workout-library.md`

Upload these files to a vector store in your Foundry project and put the
resulting ID into `agent.yaml` under `vector_store_ids` (replace
`<VECTOR_STORE_ID>`). Re-upload whenever the knowledge files change.

## MCP server

The agent connects to the managed MCP server, defined under `definition.tools`
in `agent.yaml`:

- `server_url`: `https://intervals-mcp.training-architect.com/mcp`
- `allowed_tools`: `prepare_week_data`, `get_latest_activities`,
  `list_library_workouts`, `list_standard_library_workouts`, `upload_week_plan`

### Per-request credentials (no stored connection)

Authentication is **not** stored in a Foundry project connection. Instead, the
calling application supplies the athlete id and API key per request as
structured inputs, and the agent forwards them as headers to the MCP server:

```yaml
headers:
  X-Intervals-Athlete-Id: "{{intervals_athlete_id}}"
  X-Intervals-Api-Key: "{{intervals_api_key}}"
```

The matching structured inputs `intervals_athlete_id` and `intervals_api_key`
are declared in `agent.yaml`. At runtime, supply them through the Responses API:

```python
project_client = AIProjectClient(endpoint=project_endpoint, credential=credential, allow_preview=True)
openai_client = project_client.get_openai_client(agent_name="training-architect-agent")

response = openai_client.responses.create(
    input="Plan my next week",
    extra_body={
        "structured_inputs": {
            "discipline": "marathon",
          "response_language": "en",
            "intervals_athlete_id": athlete_id,  # entered by the user in your app
            "intervals_api_key": api_key,         # kept client-side; sent over TLS only
        },
    },
)
```

> **Security:** The API key is passed per request. Send it only over TLS, never
> log it, and do not persist it server-side. This keeps credentials out of the
> repo, CI, and any stored Foundry connection, and makes the agent multi-user
> ready (each call uses the caller's own credentials).

### Testing the agent (no Playground)

Because credentials are runtime structured inputs, the Foundry **Playground**
cannot exercise the MCP tools — it does not send `structured_inputs`, so the
`X-Intervals-*` headers would be empty. No project connection is required, and
deleting an old connection does not change this.

To test the real production path, use `invoke_agent.py`, which calls the agent
through the Responses API with your values. It reads configuration from a `.env`
file (or the environment) — see `.env.example`:

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
ATHLETE_ID=i12345
INTERVALS_API_KEY=<your-api-key>
```

```powershell
pip install -r foundry-agent/requirements.txt
$env:DISCIPLINE = "marathon"   # optional, default climber
$env:RESPONSE_LANGUAGE = "de"  # optional, default de
python foundry-agent/invoke_agent.py
```

For a multi-turn dialog (the agent keeps context across questions), use the
interactive chat mode. It chains each turn with `previous_response_id`, which
keeps context even when the Conversations endpoint is unavailable:

```powershell
python foundry-agent/invoke_agent.py --chat
```

The structured inputs (`discipline`, `response_language`, `intervals_athlete_id`, `intervals_api_key`)
are sent on every turn — they are per-request.

The script authenticates to Foundry with `DefaultAzureCredential` (`az login`)
and passes `discipline`, `response_language`, `intervals_athlete_id`, and
`intervals_api_key` as structured inputs — exactly as your application will.

### Tracing (Application Insights)

Agent tracing linkage to Application Insights is currently treated as a
separate configuration step in Foundry.

- It is **not** part of `agent.yaml`.
- It is **not** set by `deploy_agent.py`.
- It is **not** configured by `foundry-agent/infra/main.bicep`.

Use the Foundry UI (`Ablaufverfolgungen` -> `Verbinden`) to connect the agent
to an existing Application Insights resource.

If you already use a central App Insights instance for the webservice, reuse the
same instance for the agent traces to keep monitoring consolidated.

## CI/CD deployment

`deploy_agent.py` publishes a new agent version and (re)builds the vector store
from the `coach-logic/` files in one run. It authenticates with
`DefaultAzureCredential`, so it works locally (`az login`) and in GitHub Actions
via OIDC.

### Local run

```powershell
pip install -r foundry-agent/requirements.txt
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<resource>.services.ai.azure.com/api/projects/<project>"
python foundry-agent/deploy_agent.py
```

The script:

1. Reuses the vector store named `coach-logic` (or creates it on first run),
   refreshing its files from the six knowledge files each time.
2. Embeds all discipline profiles into the instructions placeholder.
3. Sets the vector store id on the `file_search` tool.
4. Upserts the agent version through the Azure AI Projects SDK.

### Dry run (preview without deploying)

To see the final assembled definition without contacting Foundry or building a
vector store:

```powershell
python foundry-agent/deploy_agent.py --dry-run
```

This writes the rendered output to `foundry-agent/.rendered/` (git-ignored):

- `instructions.txt` — instructions with all discipline profiles embedded
- `agent.definition.json` — the full agent definition that would be deployed

The `file_search` tool still shows the `<VECTOR_STORE_ID>` placeholder in a dry
run; the real id is only set during an actual deploy. No Azure credentials are
required for the dry run.

### Update only the knowledge (vector store)

To refresh the `coach-logic` vector store without publishing a new agent
version (e.g. after editing only the knowledge files):

```powershell
python foundry-agent/deploy_agent.py --vector-store-only
```

This reuses the existing `coach-logic` store (or creates it on first run),
re-uploads the six knowledge files, and prints the vector store id. Because the
agent already references the store by id, no agent update is needed.

### GitHub Actions

The workflow [`.github/workflows/deploy-agent.yml`](../.github/workflows/deploy-agent.yml)
runs the script on changes to `foundry-agent/**`, `coach-logic/**`, or the
discipline prompts, and can also be triggered manually. The discipline is no
longer a deploy-time choice — it is selected at runtime via the `discipline`
structured input.

Required GitHub secrets (the OIDC ones already exist for the webservice deploy):

| Secret | Purpose |
| ------ | ------- |
| `AZURE_CLIENT_ID` | OIDC service principal client id |
| `AZURE_TENANT_ID` | Entra tenant id |
| `AZURE_SUBSCRIPTION_ID` | Subscription id |
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint URL |

The same OIDC service principal used by the webservice deployment is reused for
Foundry workflows (`AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID`).
That principal needs:

- a data-plane role on the Foundry project (e.g. `Foundry User`) to create
  vector stores and agent versions.
- control-plane permissions on the Foundry resource group (at least
  `Contributor`, or equivalent) to run the `infra-agent.yml` Bicep deployment.

## Infrastructure (Bicep)

The Foundry **control-plane** resources are described in
[`infra/main.bicep`](infra/main.bicep): the Azure AI Services (Foundry) account,
the Foundry project, the model deployment (`gpt-4.1-mini`), and an RBAC role
assignment that grants the deployment service principal data-plane access.

The agent and the vector store are **data-plane** objects and stay with
`deploy_agent.py` — they are intentionally not in Bicep.

This deploys a **fresh** Foundry account + project from scratch, into its own
resource group (separate from the MCP webservice, which reuses an existing App
Service Plan in a different group). Create the group first, then deploy:

```powershell
# 1. Create the dedicated Foundry resource group
az group create --name <foundry-rg> --location swedencentral

# 2. Copy and fill in real values (git-ignored)
Copy-Item foundry-agent/infra/main.bicepparam foundry-agent/infra/main.local.bicepparam

# 3. Preview
az deployment group what-if `
  --resource-group <foundry-rg> `
  --template-file foundry-agent/infra/main.bicep `
  --parameters foundry-agent/infra/main.local.bicepparam

# 4. Apply
az deployment group create `
  --resource-group <foundry-rg> `
  --template-file foundry-agent/infra/main.bicep `
  --parameters foundry-agent/infra/main.local.bicepparam
```

Or use the manual workflow
[`.github/workflows/infra-agent.yml`](../.github/workflows/infra-agent.yml)
(choose `what-if` or `apply`). It needs these additional secrets:

| Secret | Purpose |
| ------ | ------- |
| `FOUNDRY_RESOURCE_GROUP` | Resource group of the Foundry account |
| `FOUNDRY_ACCOUNT_NAME` | Foundry (AI Services) account name |
| `FOUNDRY_PROJECT_NAME` | Foundry project name |
| `FOUNDRY_LOCATION` | Region (e.g. `swedencentral`) |
| `FOUNDRY_MODEL_VERSION` | Model version for the deployment |
| `FOUNDRY_DEPLOY_PRINCIPAL_ID` | Object id of the deploy service principal |

`FOUNDRY_DEPLOY_PRINCIPAL_ID` should be the object id of that same deployment
service principal, unless you intentionally use a different identity.

> **Verify the role:** `deployRoleDefinitionId` defaults to the built-in
> **Azure AI User** role. Confirm this GUID for your tenant, or override the
> parameter, before applying.

## Keeping in sync

When you change the instructions or knowledge files here, redeploy via
`deploy_agent.py` (or the workflow) to publish a new version. Keep the discipline
files and `coach-logic/` files as the single source of truth; `agent.yaml` keeps
the `<VECTOR_STORE_ID>` placeholder, because the id is generated at deploy time.
