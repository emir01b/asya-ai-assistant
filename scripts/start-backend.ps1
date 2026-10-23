param([switch]$Reload, [string]$LanAddress = '', [switch]$Https)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Mevcut .venv bulunamadı.' }
Set-Location -LiteralPath $ProjectRoot
$BindAddress = '127.0.0.1'
if ($LanAddress) {
    $LanInterface = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop
    $AddressBytes = ([ipaddress]::Parse($LanAddress)).GetAddressBytes()
    if (-not ($AddressBytes[0] -eq 10 -or ($AddressBytes[0] -eq 172 -and $AddressBytes[1] -ge 16 -and $AddressBytes[1] -le 31) -or ($AddressBytes[0] -eq 192 -and $AddressBytes[1] -eq 168))) {
        throw 'LanAddress bu bilgisayardaki özel bir IPv4 adresi olmalıdır.'
    }
    $BindAddress = '0.0.0.0'
    Write-Host "Yerel ağ arayüzü: $LanAddress ($($LanInterface.InterfaceAlias))"
}
$env:VOICE_LAN_IP = $LanAddress
$env:VOICE_LAN_HTTPS = if ($Https) { '1' } else { '0' }
if (& (Join-Path $PSScriptRoot 'check-running-server.ps1') -LanAddress $LanAddress -Https:$Https) {
    return
}
if ($Https) {
    if (-not $LanAddress -or $Reload) { throw 'HTTPS için LAN adresi gerekir; reload desteklenmez.' }
    Write-Host "HTTPS: https://${LanAddress}:8000"
    & $PythonExe -m apps.backend.app.serve_lan
    exit $LASTEXITCODE
}
$UvicornArgs = @('-m', 'uvicorn', 'apps.backend.app.main:app', '--host', $BindAddress, '--port', '8000', '--ws-max-size', '32768', '--limit-concurrency', '64')
if ($Reload) { $UvicornArgs += @('--reload', '--reload-dir', 'apps/backend/app') }
& $PythonExe @UvicornArgs
exit $LASTEXITCODE
