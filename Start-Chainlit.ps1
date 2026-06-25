param(
    [int]$Port = 8013,
    [switch]$Watch
)

if ($IsWindows) {
    $pythonExe = Join-Path $PSScriptRoot ".venv312\Scripts\python.exe"
    $createHint = "py -3.12 -m venv .venv312"
} else {
    $pythonExe = Join-Path $PSScriptRoot ".venv312/bin/python3"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = Join-Path $PSScriptRoot ".venv312/bin/python"
    }
    $createHint = "python3.12 -m venv .venv312"
}

$appPath = Join-Path $PSScriptRoot "foundry-agent/chainlit_app.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Chainlit environment not found at .venv312. Create it first: $createHint"
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
