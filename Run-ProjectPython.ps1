param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Project virtual environment not found at .venv. Create it first: py -3.14 -m venv .venv"
    exit 1
}

& $pythonExe @Args
exit $LASTEXITCODE
