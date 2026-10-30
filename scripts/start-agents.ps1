param([switch]$Install, [string]$LanAddress = '', [string]$Certificate = '', [string]$PrivateKey = '')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$AgentPython = Join-Path $ProjectRoot '.venv-agents\Scripts\python.exe'
if ($Install) {
    if (-not (Test-Path -LiteralPath $AgentPython)) {
        & py -3.11 -m venv .venv-agents
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 gerekli: https://www.python.org/downloads/release/python-3119/' }
    }
    & $AgentPython -m pip install -r apps/agents/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Ajan bağımlılıkları kurulamadı.' }
}
if (-not (Test-Path -LiteralPath $AgentPython)) { throw 'Önce scripts/start-agents.ps1 -Install çalıştırın.' }
$AgentArgs = @('-m', 'apps.agents.serve')
if ($LanAddress) {
    Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop | Out-Null
    $AgentArgs += @('--lan-address', $LanAddress, '--cert', $Certificate, '--key', $PrivateKey)
}
& $AgentPython @AgentArgs
exit $LASTEXITCODE
