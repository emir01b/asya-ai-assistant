param([string]$LanAddress = '', [switch]$Https)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (& (Join-Path $PSScriptRoot 'check-running-server.ps1') -LanAddress $LanAddress -Https:$Https) {
    return
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'apps\frontend\dist\index.html'))) {
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'apps\frontend')
    try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build başarısız.' } }
    finally { Pop-Location }
}
if ($Https) { Write-Host 'Bu bilgisayarda: http://127.0.0.1:8001' }
else { Write-Host 'ASYA: http://127.0.0.1:8000' }
& (Join-Path $PSScriptRoot 'start-backend.ps1') -LanAddress $LanAddress -Https:$Https
