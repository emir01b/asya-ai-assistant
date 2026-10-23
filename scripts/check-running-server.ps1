param([string]$LanAddress = '', [switch]$Https)
$ErrorActionPreference = 'Stop'
$VoiceProjectRoot = Split-Path -Parent $PSScriptRoot
$VoicePython = Join-Path $VoiceProjectRoot '.venv\Scripts\python.exe'
$VoiceProbeArgs = @('-m', 'apps.backend.app.server_probe')
if ($LanAddress) { $VoiceProbeArgs += @('--lan-address', $LanAddress) }
if ($Https) { $VoiceProbeArgs += '--https' }
Push-Location -LiteralPath $VoiceProjectRoot
try {
    $VoiceProbeOutput = & $VoicePython @VoiceProbeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Sunucu durumu kontrol edilemedi.' }
    $VoiceProbe = $VoiceProbeOutput | ConvertFrom-Json
} finally { Pop-Location }
if ($VoiceProbe.state -eq 'running') {
    Write-Host 'ASYA zaten çalışıyor. İkinci sunucu başlatılmadı.'
    Write-Host "Uygulama: $($VoiceProbe.url)"
    if ($VoiceProbe.local_url -ne $VoiceProbe.url) {
        Write-Host "Bu bilgisayarda: $($VoiceProbe.local_url)"
    }
    return $true
}
if ($VoiceProbe.state -ne 'free') {
    throw "Port kullanımda ($($VoiceProbe.ports -join ', ')). $($VoiceProbe.reason) Mevcut sunucunun terminalinde Ctrl+C ile durdurup tekrar deneyin."
}
return $false
