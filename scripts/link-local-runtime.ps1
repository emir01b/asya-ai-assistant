param([string]$RuntimeRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\voice-lab'))
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = (Resolve-Path -LiteralPath $RuntimeRoot).Path
if ($RuntimeRoot -eq $ProjectRoot) { throw 'RuntimeRoot farklı bir klasör olmalıdır.' }
$RuntimeNames = @('.venv', '.venv-stt', 'data', 'chatterbox')
foreach ($RuntimeName in $RuntimeNames) {
    $RuntimeTarget = Join-Path $RuntimeRoot $RuntimeName
    if (-not (Test-Path -LiteralPath $RuntimeTarget -PathType Container)) {
        throw "Gerekli yerel klasör bulunamadı: $RuntimeTarget"
    }
    $RuntimeLink = Join-Path $ProjectRoot $RuntimeName
    $ExistingItem = Get-Item -LiteralPath $RuntimeLink -Force -ErrorAction SilentlyContinue
    if ($ExistingItem -and ($ExistingItem.LinkType -ne 'Junction' -or $ExistingItem.Target -ne $RuntimeTarget)) {
        throw "Hedef zaten var; mevcut dosyalara dokunulmadı: $RuntimeLink"
    }
}
foreach ($RuntimeName in $RuntimeNames) {
    $RuntimeTarget = Join-Path $RuntimeRoot $RuntimeName
    $RuntimeLink = Join-Path $ProjectRoot $RuntimeName
    if (-not (Test-Path -LiteralPath $RuntimeLink)) {
        New-Item -ItemType Junction -Path $RuntimeLink -Target $RuntimeTarget | Out-Null
    }
    Write-Host "$RuntimeName -> $RuntimeTarget"
}
Write-Host 'Yerel ortam bağlandı. voice-lab klasörünü koruyun; iki backend aynı anda çalıştırılmamalıdır.'
