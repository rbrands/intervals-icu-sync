@description('Name of the Web App to create.')
param appName string

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Name of the existing App Service Plan to deploy into.')
param appServicePlanName string

@description('Name of the existing Application Insights instance. Leave empty to skip.')
param appInsightsName string = ''

@description('Optional custom domain (e.g. intervals-mcp.training-architect.com). Leave empty to use only the azurewebsites.net hostname.')
param customDomain string = ''

@description('Fernet key for stateless OAuth tokens. Leave empty to use an ephemeral key (tokens lost on restart).')
@secure()
param oauthTokenSecret string = ''

@description('OAuth access token lifetime in days. Default is 30.')
param oauthAccessTokenLifetimeDays string = '30'

@description('Athlete ID whose shared workout library is exposed as standard library. Leave empty to disable.')
param standardLibraryAthleteId string = ''

@description('Enable MCP response JSON preview tracing. Keep false in normal production operation.')
param mcpTraceResponseJson string = 'false'

@description('Max UTF-8 bytes captured as MCP response preview when response JSON tracing is enabled.')
param mcpTraceResponsePreviewLimit string = '4096'

@description('Log level for structured MCP RPC events (INFO, WARNING, ERROR).')
param mcpRpcEventLogLevel string = 'INFO'

@description('Name of the existing Storage Account used for OAuth client registry table data.')
param oauthClientStorageAccountName string = 'stbrandsadvisorycentral'

@description('Name of the Azure Table used to persist OAuth client registrations.')
param oauthClientTableName string = 'mcpoauthclients'

// Reference the existing App Service Plan – it is not modified.
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' existing = {
  name: appServicePlanName
}

// Reference the existing Application Insights instance (if provided).
resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = if (appInsightsName != '') {
  name: appInsightsName
}

var tags = {
  project: 'intervals-icu-sync'
  'managed-by': 'bicep'
  tier: 'application'
}

// Application Insights connection string setting (empty array when AI is not configured).
var appInsightsSettings = appInsightsName != '' ? [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights!.properties.ConnectionString
  }
] : []

// Fernet key setting for stateless OAuth tokens (empty array when secret is not configured).
var oauthTokenSettings = oauthTokenSecret != '' ? [
  {
    name: 'OAUTH_TOKEN_SECRET'
    value: oauthTokenSecret
  }
] : []

// Standard library athlete setting (empty array when not configured).
var standardLibrarySettings = standardLibraryAthleteId != '' ? [
  {
    name: 'STANDARD_LIBRARY_ATHLETE_ID'
    value: standardLibraryAthleteId
  }
] : []

// Shared app settings used by the production slot and all deployment slots.
var commonAppSettings = [
  {
    name: 'MCP_TRANSPORT'
    value: 'sse'
  }
  {
    name: 'FASTMCP_HOST'
    value: '0.0.0.0'
  }
  {
    name: 'FASTMCP_PORT'
    value: '8000'
  }
  {
    name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
    value: 'true'
  }
  {
    name: 'ENABLE_ORYX_BUILD'
    value: 'true'
  }
  {
    name: 'MCP_TRACE_RESPONSE_JSON'
    value: mcpTraceResponseJson
  }
  {
    name: 'MCP_TRACE_RESPONSE_PREVIEW_LIMIT'
    value: mcpTraceResponsePreviewLimit
  }
  {
    name: 'MCP_RPC_EVENT_LOG_LEVEL'
    value: mcpRpcEventLogLevel
  }
  {
    name: 'OAUTH_ACCESS_TOKEN_LIFETIME_DAYS'
    value: oauthAccessTokenLifetimeDays
  }
  {
    name: 'OAUTH_CLIENT_STORAGE_ACCOUNT'
    value: oauthClientStorageAccountName
  }
  {
    name: 'OAUTH_CLIENT_TABLE_NAME'
    value: oauthClientTableName
  }
]

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  tags: union(tags, { environment: 'prod' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000'
      alwaysOn: true
      healthCheckPath: '/health'
      appSettings: union(commonAppSettings, appInsightsSettings, oauthTokenSettings, standardLibrarySettings, [
        {
          name: 'FASTMCP_ALLOWED_HOST'
          // Comma-separated: azurewebsites.net hostname + optional custom domain.
          value: customDomain != '' ? '${appName}.azurewebsites.net,${customDomain}' : '${appName}.azurewebsites.net'
        }
      ])
    }
  }
}

// FASTMCP_ALLOWED_HOST must be a slot-sticky setting so it does NOT swap
// with the code. Each slot keeps its own hostname value after a swap.
// OAUTH_TOKEN_SECRET is also sticky: the Fernet key must stay with the
// production slot so tokens remain valid across deployments and swaps.
resource slotConfigNames 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: webApp
  name: 'slotConfigNames'
  properties: {
    appSettingNames: ['FASTMCP_ALLOWED_HOST', 'OAUTH_TOKEN_SECRET']
  }
}

// Monitoring Metrics Publisher (built-in role) – grants each slot's Managed Identity
// the right to send telemetry to Application Insights. This avoids storing the
// instrumentation key as a usable credential: auth is handled via Entra ID tokens.
var monitoringPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource aiRoleProduction 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (appInsightsName != '') {
  name: guid(webApp.id, appInsights.id, monitoringPublisherRoleId)
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringPublisherRoleId)
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiRoleStaging 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (appInsightsName != '') {
  name: guid(stagingSlot.id, appInsights.id, monitoringPublisherRoleId)
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringPublisherRoleId)
    principalId: stagingSlot.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiRoleDev 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (appInsightsName != '') {
  name: guid(devSlot.id, appInsights.id, monitoringPublisherRoleId)
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringPublisherRoleId)
    principalId: devSlot.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource stagingSlot 'Microsoft.Web/sites/slots@2023-01-01' = {
  parent: webApp
  name: 'staging'
  location: location
  kind: 'app,linux'
  tags: union(tags, { environment: 'staging' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000'
      alwaysOn: false
      healthCheckPath: '/health'
      appSettings: union(commonAppSettings, appInsightsSettings, oauthTokenSettings, standardLibrarySettings, [
        {
          name: 'FASTMCP_ALLOWED_HOST'
          value: '${appName}-staging.azurewebsites.net'
        }
      ])
    }
  }
}

resource devSlot 'Microsoft.Web/sites/slots@2023-01-01' = {
  parent: webApp
  name: 'dev'
  location: location
  kind: 'app,linux'
  tags: union(tags, { environment: 'dev' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python -m uvicorn webservice.mcp_server:app --host 0.0.0.0 --port 8000'
      alwaysOn: false
      healthCheckPath: '/health'
      appSettings: union(commonAppSettings, appInsightsSettings, oauthTokenSettings, standardLibrarySettings, [
        {
          name: 'FASTMCP_ALLOWED_HOST'
          value: '${appName}-dev.azurewebsites.net'
        }
      ])
    }
  }
}

@description('Default HTTPS URL of the deployed Web App (production slot).')
output appUrl string = 'https://${webApp.properties.defaultHostName}'

@description('HTTPS URL of the staging deployment slot.')
output stagingUrl string = 'https://${stagingSlot.properties.defaultHostName}'

@description('HTTPS URL of the dev deployment slot.')
output devUrl string = 'https://${devSlot.properties.defaultHostName}'

@description('Resource name of the Web App.')
output appName string = webApp.name

@description('Managed Identity principal id for the production slot.')
output productionPrincipalId string = webApp.identity.principalId

@description('Managed Identity principal id for the staging slot.')
output stagingPrincipalId string = stagingSlot.identity.principalId

@description('Managed Identity principal id for the dev slot.')
output devPrincipalId string = devSlot.identity.principalId
