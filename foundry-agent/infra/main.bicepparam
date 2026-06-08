// Example parameters for foundry-agent/infra/main.bicep.
// Copy to main.local.bicepparam, fill in real values, and keep that file out of
// source control (it is git-ignored). Deploys a fresh Foundry account + project.
using './main.bicep'

// Names for the new resources.
param foundryAccountName = 'training-architect'
param foundryProjectName = 'training-architect'
param location = 'swedencentral'

// Model deployment referenced by foundry-agent/agent.yaml (definition.model).
param modelDeploymentName = 'gpt-4.1-mini'
param modelName = 'gpt-4.1-mini'
// Verify this version is available for gpt-4.1-mini in the chosen region:
//   az cognitiveservices model list --location swedencentral --query "[?model.name=='gpt-4.1-mini'].model.version" -o tsv
param modelVersion = '2025-04-14'
param modelSkuName = 'GlobalStandard'
param modelCapacity = 50

// Resource tags applied to Foundry account and project.
param tags = {
	project: 'intervals-icu-sync'
	'managed-by': 'bicep'
	tier: 'application'
	environment: 'prod'
}

// Object id of the deployment service principal (the one that runs
// deploy_agent.py in CI). Leave empty to skip the role assignment.
param deployPrincipalId = '<DEPLOY_SP_OBJECT_ID>'
