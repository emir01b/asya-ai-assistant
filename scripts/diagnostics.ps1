$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'check-environment.ps1')
foreach ($Endpoint in @('health','system/status','system/gpu','diagnostics')) {
    Write-Host "API: $Endpoint"
    try { Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/$Endpoint" -TimeoutSec 10 | ConvertTo-Json -Depth 8 }
    catch { Write-Warning $_.Exception.Message }
}
