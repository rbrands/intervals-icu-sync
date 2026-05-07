# Start the intervals-icu MCP server in SSE mode (non-blocking).
# The server listens on http://127.0.0.1:8765/sse
#
# Usage:
#   .\start_mcp_server.ps1          # start
#   .\start_mcp_server.ps1 -Stop    # stop a running instance

param(
    [switch]$Stop
)

$PidFile = "$PSScriptRoot\.mcp_server.pid"

if ($Stop) {
    if (Test-Path $PidFile) {
        $serverPid = Get-Content $PidFile
        Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
        Remove-Item $PidFile
        Write-Host "MCP server (PID $serverPid) stopped."
    } else {
        Write-Host "No running MCP server found."
    }
    exit
}

$python = "$PSScriptRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

# Read FASTMCP_ALLOWED_HOST from .env (if present)
$allowedHost = ""
$envFile = "$PSScriptRoot\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^FASTMCP_ALLOWED_HOST=(.+)$') {
            $allowedHost = $Matches[1].Trim()
        }
    }
}

$allowedHostFragment = if ($allowedHost) { "`$env:FASTMCP_ALLOWED_HOST='$allowedHost'; " } else { "" }
$cmd = "`$env:MCP_TRANSPORT='sse'; `$env:FASTMCP_HOST='127.0.0.1'; `$env:FASTMCP_PORT='8765'; ${allowedHostFragment}& '$python' '$PSScriptRoot\scripts\mcp_server.py'"

$proc = Start-Process pwsh `
    -ArgumentList "-NoExit", "-Command", $cmd `
    -WorkingDirectory $PSScriptRoot `
    -PassThru

$proc.Id | Set-Content $PidFile
Write-Host "MCP server started (PID $($proc.Id)) → http://127.0.0.1:8765/sse"
Write-Host "Stop with: .\start_mcp_server.ps1 -Stop"
