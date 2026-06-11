# Copy this file to config.ps1 (in the repo root) and fill in your values.
# NEVER commit config.ps1 to source control.
#
# This is the project-wide deployment config. It covers BOTH the MCP webservice
# and the Foundry agent infrastructure.
#
# Usage (from the repo root):
#   .\setup.ps1 -Bicep      # generate both infra/main.local.bicepparam files
#   .\setup.ps1 -GitHub     # push all values as GitHub Actions secrets
#   .\setup.ps1 -All        # both

$config = @{
    # --- Shared Azure / OIDC ------------------------------------------------

    # Azure subscription
    SubscriptionId       = "__SUBSCRIPTION_ID__"

    # Entra ID tenant
    TenantId             = "__TENANT_ID__"

    # Service principal used by GitHub Actions to authenticate to Azure via OIDC.
    # Create with: az ad sp create-for-rbac --name "sp-intervals-icu-deploy"
    # Then add federated credentials (branch:main and pull_request) via the Azure portal
    # or az ad app federated-credential create.
    AzureClientId        = "__AZURE_CLIENT_ID__"

    # --- MCP webservice (webservice/infra) ----------------------------------

    # Shared resource group (from brands-advisory-central-infra)
    ResourceGroup        = "__RESOURCE_GROUP__"

    # Azure region – must match the resource group location
    Location             = "germanywestcentral"

    # Web App name (globally unique across all Azure App Services)
    AppName              = "ta-intervals-mcp"

    # Name of the existing App Service Plan (from brands-advisory-central-infra)
    AppServicePlanName   = "__APP_SERVICE_PLAN_NAME__"

    # Name of the existing Application Insights instance (from brands-advisory-central-infra)
    AppInsightsName      = "__APP_INSIGHTS_NAME__"

    # Optional custom domain for the production slot.
    # Leave empty string to use only the azurewebsites.net hostname.
    CustomDomain         = "intervals-mcp...."

    # Fernet key for stateless OAuth tokens (survives server restarts).
    # Generate once with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Store in Azure App Service Application Settings as OAUTH_TOKEN_SECRET.
    # If not set, an ephemeral key is generated at startup (tokens lost on restart).
    OAuthTokenSecret     = "__OAUTH_TOKEN_SECRET__"

    # Athlete ID whose shared workout library should be exposed as
    # "standard library" by MCP method list_standard_library_workouts.
    StandardLibraryAthleteId = "__STANDARD_LIBRARY_ATHLETE_ID__"

    # Optional MCP response preview tracing in Application Insights.
    # Keep disabled in normal production operation to reduce telemetry volume.
    # Allowed values: true/false
    McpTraceResponseJson      = "false"

    # Max UTF-8 bytes captured as response preview when McpTraceResponseJson=true.
    McpTraceResponsePreviewLimit = "4096"

    # --- Foundry agent ------------------------------------------------------

    # Foundry project endpoint used by the "Deploy Foundry Agent" workflow
    # (foundry-agent/deploy_agent.py). Pushed as GitHub secret FOUNDRY_PROJECT_ENDPOINT.
    # Example: https://<resource>.services.ai.azure.com/api/projects/<project>
    FoundryProjectEndpoint   = "__FOUNDRY_PROJECT_ENDPOINT__"

    # Foundry infrastructure (foundry-agent/infra) — deployed by the
    # "Deploy Foundry Infrastructure" workflow. This uses its OWN resource group,
    # separate from the MCP webservice resource group above.
    FoundryResourceGroup     = "__FOUNDRY_RESOURCE_GROUP__"
    FoundryAccountName       = "training-architect"
    FoundryProjectName       = "training-architect"
    FoundryLocation          = "swedencentral"
    FoundryModelVersion      = "2025-04-14"
    # Object id of the deployment service principal (NOT the client id).
    FoundryDeployPrincipalId = "__FOUNDRY_DEPLOY_PRINCIPAL_ID__"
}
