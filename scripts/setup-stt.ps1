param([switch]$DownloadModel)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$SttPython = Join-Path $ProjectRoot '.venv-stt\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $SttPython)) { & $PythonExe -m venv (Join-Path $ProjectRoot '.venv-stt') }
if ($LASTEXITCODE -ne 0) { throw 'STT ortamı oluşturulamadı.' }
& $SttPython -m pip install -r (Join-Path $ProjectRoot 'apps\backend\requirements-stt.txt')
if ($LASTEXITCODE -ne 0) { throw 'STT kurulumu başarısız.' }
if ($DownloadModel) { & $SttPython (Join-Path $PSScriptRoot 'download-stt.py') }
exit $LASTEXITCODE
