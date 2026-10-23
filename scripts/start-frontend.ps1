$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $ProjectRoot 'apps\frontend')
if (-not (Test-Path -LiteralPath 'node_modules')) { throw 'Önce npm.cmd ci komutunu apps/frontend içinde çalıştırın.' }
& npm.cmd run dev
exit $LASTEXITCODE
