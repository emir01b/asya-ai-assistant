param([string]$LanAddress = '', [switch]$HttpOnly)
$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 cannot create the PEM certificates. Relaunch this
# entry point in PowerShell 7 before performing any setup or starting a server.
if ($PSVersionTable.PSVersion.Major -lt 7 -and -not $HttpOnly) {
    $VoicePwshCommand = Get-Command pwsh.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $VoicePwshCandidates = @(
        $(if ($VoicePwshCommand) { $VoicePwshCommand.Source }),
        (Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe'),
        (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    )
    $VoicePwsh = $VoicePwshCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
    if (-not $VoicePwsh) {
        throw 'PowerShell 7 (pwsh.exe) bulunamadi. PowerShell 7 kurup bu komutu yeniden calistirin.'
    }
    $VoiceForwardArgs = @('-NoLogo', '-NoProfile', '-File', $PSCommandPath)
    if ($LanAddress) { $VoiceForwardArgs += @('-LanAddress', $LanAddress) }
    Write-Host 'HTTPS icin PowerShell 7 ile devam ediliyor...'
    & $VoicePwsh @VoiceForwardArgs
    exit $LASTEXITCODE
}
if (-not $LanAddress) {
    $Configuration = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | Select-Object -First 1
    if (-not $Configuration) { throw 'Yerel ağ IPv4 adresi bulunamadı. -LanAddress ile belirtin.' }
    $LanAddress = $Configuration.IPv4Address.IPAddress | Select-Object -First 1
}
if (& (Join-Path $PSScriptRoot 'check-running-server.ps1') -LanAddress $LanAddress -Https:(-not $HttpOnly)) {
    return
}
& (Join-Path $PSScriptRoot 'enable-lan-access.ps1') -LanAddress $LanAddress
if (-not $HttpOnly) {
    & (Join-Path $PSScriptRoot 'setup-lan-https.ps1') -LanAddress $LanAddress
    Write-Host "Mikrofon için diğer cihazdan açın: https://${LanAddress}:8000"
} else {
    Write-Host "Diğer cihazdan açın: http://${LanAddress}:8000"
}
& (Join-Path $PSScriptRoot 'start-app.ps1') -LanAddress $LanAddress -Https:(-not $HttpOnly)
