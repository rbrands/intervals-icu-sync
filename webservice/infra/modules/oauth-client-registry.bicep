@description('Name of the existing Storage Account that should hold OAuth client registry data.')
param storageAccountName string = 'stbrandsadvisorycentral'

@description('Name of the Azure Table used to persist OAuth client registrations.')
param tableName string = 'mcpoauthclients'

@description('Managed Identity principal id for the production App Service slot.')
param productionPrincipalId string

@description('Managed Identity principal id for the staging App Service slot.')
param stagingPrincipalId string

@description('Managed Identity principal id for the dev App Service slot.')
param devPrincipalId string

// Reference the existing Storage Account that hosts the OAuth client table.
resource oauthClientStorage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource oauthClientTableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' existing = {
  parent: oauthClientStorage
  name: 'default'
}

// Ensure the OAuth client registry table exists.
resource oauthClientRegistryTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = {
  parent: oauthClientTableService
  name: tableName
}

// Storage Table Data Contributor: allows the App Service identities to read/write OAuth client registrations.
var storageTableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'

resource oauthTableRoleProduction 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(productionPrincipalId, oauthClientStorage.id, storageTableDataContributorRoleId)
  scope: oauthClientStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
    principalId: productionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource oauthTableRoleStaging 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(stagingPrincipalId, oauthClientStorage.id, storageTableDataContributorRoleId)
  scope: oauthClientStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
    principalId: stagingPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource oauthTableRoleDev 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(devPrincipalId, oauthClientStorage.id, storageTableDataContributorRoleId)
  scope: oauthClientStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
    principalId: devPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the registry table.')
output registryTableName string = oauthClientRegistryTable.name
