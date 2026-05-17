<#
.SYNOPSIS
    Validates and optionally deploys Bicep infrastructure.

.DESCRIPTION
    Runs az bicep lint + az deployment group what-if.
    With -Deploy, performs the actual deployment after a confirmation prompt.
    Requires config.ps1 and infra/main.local.bicepparam (run setup.ps1 -Bicep first).

.PARAMETER Deploy
    When specified, runs az deployment group create after the what-if preview.

.EXAMPLE
    .\Check-Deployment.ps1           # lint + what-if only
    .\Check-Deployment.ps1 -Deploy   # lint + what-if + deploy (with confirmation)
#>
param(
    [switch]$Deploy
)

$configPath = Join-Path $PSScriptRoot "config.ps1"
if (-not (Test-Path $configPath)) {
    Write-Host "config.ps1 not found." -ForegroundColor Red
    Write-Host "Copy config.example.ps1 to config.ps1 and fill in your values." -ForegroundColor Yellow
    exit 1
}
. $configPath

$paramFile = Join-Path $PSScriptRoot "infra/main.local.bicepparam"
if (-not (Test-Path $paramFile)) {
    Write-Host "infra/main.local.bicepparam not found. Run: .\setup.ps1 -Bicep" -ForegroundColor Red
    exit 1
}

Write-Host "Linting Bicep..." -ForegroundColor Yellow
az bicep lint --file (Join-Path $PSScriptRoot "infra/main.bicep")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bicep lint failed. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "Lint passed." -ForegroundColor Green
Write-Host ""

Write-Host "Running what-if deployment preview..." -ForegroundColor Yellow
Write-Host "Resource Group : $($config.ResourceGroup)" -ForegroundColor Cyan
Write-Host "App Name       : $($config.AppName)" -ForegroundColor Cyan
Write-Host ""

az deployment group what-if `
    --resource-group $config.ResourceGroup `
    --template-file (Join-Path $PSScriptRoot "infra/main.bicep") `
    --parameters (Join-Path $PSScriptRoot "infra/main.local.bicepparam")

if ($Deploy) {
    Write-Host ""
    $confirm = Read-Host "Proceed with actual deployment? (y/N)"
    if ($confirm -ne 'y') {
        Write-Host "Deployment cancelled." -ForegroundColor Yellow
        exit 0
    }

    Write-Host ""
    Write-Host "Deploying infrastructure..." -ForegroundColor Yellow
    az deployment group create `
        --resource-group $config.ResourceGroup `
        --template-file (Join-Path $PSScriptRoot "infra/main.bicep") `
        --parameters (Join-Path $PSScriptRoot "infra/main.local.bicepparam")

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Deployment failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "Deployment completed." -ForegroundColor Green
}
