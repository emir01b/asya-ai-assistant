$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogsDir = Join-Path $ProjectRoot 'data\logs'
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$ShellExe = (Get-Process -Id $PID).Path
$BackendScript = Join-Path $PSScriptRoot 'start-backend.ps1'
$FrontendScript = Join-Path $PSScriptRoot 'start-frontend.ps1'
$BackendProcess = Start-Process -FilePath $ShellExe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$BackendScript`"") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogsDir 'backend.log') -RedirectStandardError (Join-Path $LogsDir 'backend-error.log') -PassThru
$FrontendProcess = Start-Process -FilePath $ShellExe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$FrontendScript`"") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogsDir 'frontend.log') -RedirectStandardError (Join-Path $LogsDir 'frontend-error.log') -PassThru
Write-Host 'ASYA: http://127.0.0.1:5173'
Write-Host "Logs: $LogsDir"
Write-Host 'Durdurmak için Ctrl+C. Alt process ağaçları bu başlatıcıya aittir.'
try { while (-not $BackendProcess.HasExited -and -not $FrontendProcess.HasExited) { Start-Sleep -Seconds 1 } }
finally {
    # Only terminate the exact process trees created above, never arbitrary Python/Node processes.
    foreach ($ChildProcess in @($BackendProcess, $FrontendProcess)) {
        if (-not $ChildProcess.HasExited) { & taskkill.exe /PID $ChildProcess.Id /T /F | Out-Null }
    }
}
