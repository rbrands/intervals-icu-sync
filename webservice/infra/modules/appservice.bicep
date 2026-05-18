@description('Name of the Web App to create.')
param appName string

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Name of the existing App Service Plan to deploy into.')
param appServicePlanName string

@description('Name of the existing Application Insights instance. Leave empty to skip.')
param appInsightsName string = ''

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
    value: appInsights.properties.ConnectionString
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
]

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  tags: tags
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
      appSettings: union(commonAppSettings, appInsightsSettings, [
        {
          name: 'FASTMCP_ALLOWED_HOST'
          // Computed from the app name – no manual update needed after deploy.
          value: '${appName}.azurewebsites.net'
        }
      ])
    }
  }
}

// FASTMCP_ALLOWED_HOST must be a slot-sticky setting so it does NOT swap
// with the code. Each slot keeps its own hostname value after a swap.
resource slotConfigNames 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: webApp
  name: 'slotConfigNames'
  properties: {
    appSettingNames: ['FASTMCP_ALLOWED_HOST']
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
      appSettings: union(commonAppSettings, appInsightsSettings, [
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
      appSettings: union(commonAppSettings, appInsightsSettings, [
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
