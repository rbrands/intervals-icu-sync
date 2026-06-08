param(
    [int]$Port = 8013,
    [switch]$Watch
)

$pythonExe = Join-Path $PSScriptRoot ".venv312\Scripts\python.exe"
$appPath = Join-Path $PSScriptRoot "foundry-agent\chainlit_app.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Chainlit environment not found at .venv312. Create it first: py -3.12 -m venv .venv312"
    exit 1
}

if (-not (Test-Path $appPath)) {
    Write-Error "Chainlit app not found at foundry-agent/chainlit_app.py"
    exit 1
}

$arguments = @("-m", "chainlit", "run", $appPath, "--port", "$Port")
if ($Watch) {
    $arguments += "-w"
}

& $pythonExe @arguments
exit $LASTEXITCODE
