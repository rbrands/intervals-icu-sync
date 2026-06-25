param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

if ($IsWindows) {
    $pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    $createHint = "py -3.14 -m venv .venv"
} else {
    $pythonExe = Join-Path $PSScriptRoot ".venv/bin/python3"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = Join-Path $PSScriptRoot ".venv/bin/python"
    }
    $createHint = "python3 -m venv .venv"
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Project virtual environment not found at .venv. Create it first: $createHint"
    exit 1
}

& $pythonExe @Args
exit $LASTEXITCODE
