targetScope = 'resourceGroup'

@description('Name of the Web App to create.')
param appName string

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Name of the existing App Service Plan to deploy into.')
param appServicePlanName string

module appservice 'modules/appservice.bicep' = {
  name: 'deploy-${appName}'
  params: {
    appName: appName
    location: location
    appServicePlanName: appServicePlanName
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
