$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & '.\.venv\Scripts\python.exe' -m unittest discover -s apps/backend/tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Backend testleri başarısız.' }
    Push-Location -LiteralPath 'apps\frontend'
    try {
        & npm.cmd test
        if ($LASTEXITCODE -ne 0) { throw 'Frontend testleri başarısız.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build başarısız.' }
    } finally { Pop-Location }
} finally { Pop-Location }
