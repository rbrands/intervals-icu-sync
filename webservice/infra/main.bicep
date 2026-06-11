targetScope = 'resourceGroup'

@description('Name of the Web App to create.')
param appName string

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Name of the existing App Service Plan to deploy into.')
param appServicePlanName string

@description('Name of the existing Application Insights instance in this resource group. Leave empty to skip AI instrumentation.')
param appInsightsName string = ''

@description('Optional custom domain for the production slot (e.g. intervals-mcp.training-architect.com). Leave empty to use only the azurewebsites.net hostname.')
param customDomain string = ''

@description('Fernet key for stateless OAuth tokens. Leave empty to use an ephemeral key (tokens lost on restart).')
@secure()
param oauthTokenSecret string = ''

@description('Athlete ID whose shared workout library is exposed as standard library. Leave empty to disable.')
param standardLibraryAthleteId string = ''

@description('Enable MCP response JSON preview tracing. Keep false in normal production operation.')
param mcpTraceResponseJson string = 'false'

@description('Max UTF-8 bytes captured as MCP response preview when response JSON tracing is enabled.')
param mcpTraceResponsePreviewLimit string = '4096'

@description('Log level for structured MCP RPC events (INFO, WARNING, ERROR).')
param mcpRpcEventLogLevel string = 'INFO'

module appservice 'modules/appservice.bicep' = {
  name: 'deploy-${appName}'
  params: {
    appName: appName
    location: location
    appServicePlanName: appServicePlanName
    appInsightsName: appInsightsName
    customDomain: customDomain
    oauthTokenSecret: oauthTokenSecret
    standardLibraryAthleteId: standardLibraryAthleteId
    mcpTraceResponseJson: mcpTraceResponseJson
    mcpTraceResponsePreviewLimit: mcpTraceResponsePreviewLimit
    mcpRpcEventLogLevel: mcpRpcEventLogLevel
  }
}

@description('Default HTTPS URL of the deployed Web App.')
output appUrl string = appservice.outputs.appUrl

@description('HTTPS URL of the staging deployment slot.')
output stagingUrl string = appservice.outputs.stagingUrl

@description('HTTPS URL of the dev deployment slot.')
output devUrl string = appservice.outputs.devUrl

@description('Resource name of the Web App.')
output appName string = appservice.outputs.appName
