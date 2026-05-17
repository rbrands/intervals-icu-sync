# Copy this file to config.ps1 and fill in your values.
# NEVER commit config.ps1 to source control.
#
# Usage:
#   .\setup.ps1 -Bicep      # generate infra/main.local.bicepparam for local deploys
#   .\setup.ps1 -GitHub     # push all values as GitHub Actions secrets
#   .\setup.ps1 -All        # both

$config = @{
    # Azure subscription
    SubscriptionId       = "__SUBSCRIPTION_ID__"

    # Entra ID tenant
    TenantId             = "__TENANT_ID__"

    # Service principal used by GitHub Actions to authenticate to Azure via OIDC.
    # Create with: az ad sp create-for-rbac --name "sp-intervals-icu-deploy"
    # Then add federated credentials (branch:main and pull_request) via the Azure portal
    # or az ad app federated-credential create.
    AzureClientId        = "__AZURE_CLIENT_ID__"

    # Shared resource group (from brands-advisory-central-infra)
    ResourceGroup        = "__RESOURCE_GROUP__"

    # Azure region – must match the resource group location
    Location             = "germanywestcentral"

    # Web App name (globally unique across all Azure App Services)
    AppName              = "ta-intervals-mcp"

    # Name of the existing App Service Plan (from brands-advisory-central-infra)
    AppServicePlanName   = "__APP_SERVICE_PLAN_NAME__"
}
