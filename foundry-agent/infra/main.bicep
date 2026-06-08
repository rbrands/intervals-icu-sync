targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Foundry infrastructure for the training-architect agent.
//
// Covers the CONTROL-PLANE resources only:
//   - Azure AI Services (Foundry) account
//   - Foundry project
//   - Model deployment (e.g. gpt-4.1-mini)
//   - RBAC for the deployment service principal (data-plane access)
//
// The AGENT itself and the VECTOR STORE / knowledge files are data-plane
// objects and are managed by foundry-agent/deploy_agent.py, NOT by Bicep.
//
// This deploys a fresh Foundry account + project from scratch. It uses its own
// resource group, separate from the MCP webservice (which reuses an existing
// App Service Plan in a different group).
// ---------------------------------------------------------------------------

@description('Name of the Azure AI Services (Foundry) account.')
param foundryAccountName string

@description('Name of the Foundry project under the account.')
param foundryProjectName string

@description('Azure region for the Foundry account and project. Pick a region with the chosen model available; do NOT derive from the resource group.')
param location string = 'swedencentral'

@description('Custom subdomain name for the account. Required for project management and agents. Defaults to the account name.')
param customSubDomainName string = foundryAccountName

@description('Model deployment name as referenced in agent.yaml (definition.model).')
param modelDeploymentName string = 'gpt-4.1-mini'

@description('Model format. Use OpenAI for GPT models.')
param modelFormat string = 'OpenAI'

@description('Model name in the catalog.')
param modelName string = 'gpt-4.1-mini'

@description('Model version. Set to the version available in your region.')
param modelVersion string

@description('Deployment SKU name, e.g. GlobalStandard or Standard.')
param modelSkuName string = 'GlobalStandard'

@description('Deployment capacity (tokens-per-minute units, in thousands).')
param modelCapacity int = 50

@description('Object (principal) id of the deployment service principal that runs deploy_agent.py. Leave empty to skip the role assignment.')
param deployPrincipalId string = ''

@description('Role definition id (GUID) to grant the deploy principal data-plane access. Default is the built-in "Foundry User" role.')
param deployRoleDefinitionId string = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

// ---------------------------------------------------------------------------
// Foundry account (Azure AI Services, multi-service)
// ---------------------------------------------------------------------------
resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // Required for Foundry project management and agent endpoints.
    allowProjectManagement: true
    customSubDomainName: customSubDomainName
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// Foundry project
// ---------------------------------------------------------------------------
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: foundryProjectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// ---------------------------------------------------------------------------
// Model deployment (referenced by agent.yaml -> definition.model)
// ---------------------------------------------------------------------------
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: account
  name: modelDeploymentName
  sku: {
    name: modelSkuName
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

// ---------------------------------------------------------------------------
// RBAC: grant the deployment service principal data-plane access on the account
// ---------------------------------------------------------------------------
resource deployRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployPrincipalId)) {
  name: guid(account.id, deployPrincipalId, deployRoleDefinitionId)
  scope: account
  properties: {
    principalId: deployPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', deployRoleDefinitionId)
  }
}

@description('Resource id of the Foundry account.')
output accountId string = account.id

@description('Resource id of the Foundry project.')
output projectId string = project.id

@description('Model deployment name to use in agent.yaml.')
output modelDeploymentName string = modelDeployment.name

@description('Foundry project endpoint for FOUNDRY_PROJECT_ENDPOINT (deploy_agent.py / invoke_agent.py).')
output projectEndpoint string = 'https://${customSubDomainName}.services.ai.azure.com/api/projects/${foundryProjectName}'
