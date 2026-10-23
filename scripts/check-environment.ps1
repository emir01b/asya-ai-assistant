$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
& $PythonExe -c "import sys,torch,fastapi,soundfile; print('Python:',sys.version); print('Torch:',torch.__version__); print('CUDA:',torch.cuda.is_available()); print('GPU:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'yok'); print('FastAPI:',fastapi.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Python ortam kontrolü başarısız.' }
$NodeVersion = & node --version
Write-Host "Node: $NodeVersion"
if ([version]$NodeVersion.TrimStart('v') -lt [version]'22.12.0') { throw 'Node >=22.12.0 gerekli.' }
& nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
Write-Host "STT ortamı: $(Test-Path -LiteralPath (Join-Path $ProjectRoot '.venv-stt\Scripts\python.exe'))"
