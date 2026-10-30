# Windows PowerShell 5.1 and PowerShell 7. ASCII messages work in both consoles.
[CmdletBinding()]
param(
    [ValidateSet('Ask', 'Nvidia', 'NvidiaLegacy', 'CPU')][string]$Device = 'Ask',
    [string]$PythonPath = '',
    [switch]$SkipModels,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ChatterboxCommit = '5de7a54aa4e5e2baadb0182dde554908b48b85c2'

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Komut basarisiz (kod $LASTEXITCODE): $Exe $($Arguments -join ' ')" }
}

function Find-Python311 {
    param([string]$ExplicitPath)
    $candidates = @()
    if ($ExplicitPath) { $candidates += $ExplicitPath }
    else {
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            try {
                $found = & py.exe -3.11 -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0) { $candidates += $found }
            } catch { } # Launcher stderr is terminating in Windows PowerShell 5.1.
        }
        $candidates += @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
            (Join-Path $env:ProgramFiles 'Python311\python.exe')
        )
        $onPath = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($onPath) { $candidates += $onPath.Source }
    }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $result = & $candidate -c 'import sys,sysconfig; print(sys.version_info[:2] == (3,11) and sysconfig.get_platform() == ''win-amd64'')' 2>$null
            if ($LASTEXITCODE -eq 0 -and $result -eq 'True') { return $candidate }
        } catch { continue }
    }
    throw @'
Python 3.11 (64-bit) bulunamadi. Bu otomatik kurulum Python 3.11 gerektirir.
Indirme: https://www.python.org/downloads/windows/
Python 3.11.9 Windows x64 kurucusu:
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
Kurulumda Python Launcher ve Add python.exe to PATH seceneklerini secin.
Sonra bu pencereyi kapatip kurulum.bat dosyasini yeniden acin.
Baska surumleriniz silinmez. Ozel konum: .\kurulum.ps1 -PythonPath 'C:\...\python.exe'
'@
}

function Assert-ServerStopped {
    foreach ($port in @(8000, 8001)) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $task = $client.ConnectAsync('127.0.0.1', $port)
            try { $connected = $task.Wait(400) -and $client.Connected } catch { $connected = $false }
            if ($connected) { throw "Port $port kullanimda. ASYA'yi kendi terminalinde Ctrl+C ile durdurup tekrar deneyin." }
        } finally { $client.Dispose() }
    }
}

function Prepare-Venv {
    param(
        [ValidateSet('.venv', '.venv-stt')][string]$Name,
        [string]$BasePython,
        [string]$EnvironmentRoot = $ProjectRoot
    )
    $rootPath = [IO.Path]::GetFullPath($EnvironmentRoot).TrimEnd('\')
    $directory = [IO.Path]::GetFullPath((Join-Path $rootPath $Name))
    if ((Split-Path -Parent $directory) -ne $rootPath) { throw 'Guvenli olmayan ortam yolu.' }
    $existing = Get-Item -LiteralPath $directory -Force -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "$Name bir junction/sembolik baglanti. Bagli ortama dokunulmadi. Mevcut ortami scripts/link-local-runtime.ps1 ile yonetin."
        }
        Write-Host "`n$Name zaten var. Paketleri guncellemek mevcut ortami degistirir."
        Write-Host 'Y = Klasoru yedekle ve yeni Python 3.11 ortami olustur (onerilen)'
        Write-Host 'G = Python 3.11 ise mevcut ortamdaki paketleri guncelle'
        Write-Host 'Diger/Enter = Iptal'
        $answer = Read-Host 'Seciminiz'
        if ($answer -ieq 'Y') {
            $backup = "$directory.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$([guid]::NewGuid().ToString('N').Substring(0,6))"
            if ((Split-Path -Parent $backup) -ne $rootPath) { throw 'Guvenli olmayan yedek yolu.' }
            Write-Host "Ortam klasoru: $directory"
            # Both paths stay under the explicit root. No deletion.
            Move-Item -LiteralPath $directory -Destination $backup
            Write-Host "Yedek: $backup"
            Write-Host 'Geri almak icin yeni ortami baska ada tasiyip yedegin eski adini geri verin.'
        } elseif ($answer -ieq 'G') {
            $envPython = Join-Path $directory 'Scripts\python.exe'
            $valid = & $envPython -c 'import sys,sysconfig; print(sys.version_info[:2] == (3,11) and sysconfig.get_platform() == ''win-amd64'')'
            if ($LASTEXITCODE -ne 0 -or $valid -ne 'True') { throw "$Name Python 3.11 x64 degil. Tekrar calistirip Y secin." }
            return $envPython
        } else { throw 'Kurulum kullanici tarafindan iptal edildi.' }
    }
    Invoke-Checked $BasePython @('-m', 'venv', $directory)
    return (Join-Path $directory 'Scripts\python.exe')
}

function Initialize-Chatterbox {
    $source = Join-Path $ProjectRoot 'chatterbox'
    if (-not (Test-Path -LiteralPath $source)) {
        Invoke-Checked git @('init', $source)
        Invoke-Checked git @('-C', $source, 'remote', 'add', 'origin', 'https://github.com/resemble-ai/chatterbox.git')
        Invoke-Checked git @('-C', $source, 'fetch', '--depth', '1', 'origin', $ChatterboxCommit)
        Invoke-Checked git @('-C', $source, 'checkout', '--detach', 'FETCH_HEAD')
    }
    $item = Get-Item -LiteralPath $source -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'chatterbox baglantili bir klasor; kaynak degistirilmedi.' }
    $head = & git -C $source rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head -ne $ChatterboxCommit) {
        throw 'chatterbox klasoru beklenen surumde degil. Icerik korundu. Klasoru baska ada tasiyip tekrar deneyin.'
    }
    $patch = Join-Path $ProjectRoot 'patches\chatterbox-runtime.patch'
    try {
        & git -C $source apply --reverse --check $patch 2>$null
        if ($LASTEXITCODE -eq 0) { return }
    } catch { } # A patch not yet applied is expected, including on PowerShell 5.1.
    Invoke-Checked git @('-C', $source, 'apply', '--check', $patch)
    Invoke-Checked git @('-C', $source, 'apply', $patch)
}

function Start-AsyaSetup {
    Write-Host '=== ASYA ilk kullanici kurulumu (Windows x64 / Python 3.11) ==='
    $basePython = Find-Python311 $PythonPath
    Write-Host "Python 3.11 x64: $basePython"
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Node.js >=22.12.0 ve npm gerekli. LTS indirin: https://nodejs.org/en/download'
    }
    $nodeVersion = & node.exe --version
    if ($LASTEXITCODE -ne 0 -or [version]$nodeVersion.TrimStart('v') -lt [version]'22.12.0') {
        throw 'Node.js >=22.12.0 gerekli: https://nodejs.org/en/download'
    }
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        throw 'Git for Windows gerekli: https://git-scm.com/downloads/win'
    }
    Write-Host "Node: $nodeVersion; Git mevcut."
    Write-Host 'NVIDIA surucusu/karti (varsa):'
    $nvidiaReady = $false
    if (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue) {
        & nvidia-smi.exe --query-gpu=name,driver_version,memory.total --format=csv,noheader
        $nvidiaReady = $LASTEXITCODE -eq 0
        if (-not $nvidiaReady) { Write-Host 'NVIDIA sorgusu basarisiz; CPU secenegini kullanabilirsiniz.' }
    } else { Write-Host 'nvidia-smi bulunamadi. NVIDIA surucusu: https://www.nvidia.com/Download/index.aspx' }
    if ($CheckOnly) { Write-Host 'On kontrol tamam. Hicbir paket/ortam/ayar degistirilmedi.'; return }
    Assert-ServerStopped
    $choice = $Device
    if ($choice -eq 'Ask') {
        Write-Host "`nHangi ekran kartini kullaniyorsunuz?"
        Write-Host '1 = NVIDIA RTX 20/30/40/50 veya daha yeni uyumlu kart (CUDA 12.8)'
        Write-Host '2 = Eski NVIDIA GTX 10/16 vb. (CUDA 12.6; uyumluluk test edilecek)'
        Write-Host '3 = AMD / Intel / ekran karti yok / CPU ile calis (daha yavas)'
        $inputDevice = Read-Host 'Secim [1/2/3] (Enter = iptal)'
        $choice = switch ($inputDevice) { '1' { 'Nvidia' } '2' { 'NvidiaLegacy' } '3' { 'CPU' } default { throw 'Gecerli secim yapilmadi; iptal edildi.' } }
    }
    if ($choice -ne 'CPU' -and -not $nvidiaReady) {
        throw 'NVIDIA karti/surucusu dogrulanamadi. Surucunuzu kurun veya CPU secin: https://www.nvidia.com/Download/index.aspx'
    }
    $index = switch ($choice) { 'Nvidia' { 'cu128' } 'NvidiaLegacy' { 'cu126' } 'CPU' { 'cpu' } }
    $targetDevice = if ($choice -eq 'CPU') { 'cpu' } else { 'cuda' }
    Write-Host "`nSecilen: $choice / Torch 2.10.0 / $index"
    Write-Host 'CUDA Toolkit veya surucu otomatik kurulmaz; Torch kendi calisma kutuphanelerini getirir.'
    Write-Host 'Tam kurulum: yaklasik 7-10 GB indirme (Whisper dahil), en az 25 GB bos alan onerilir.'
    Write-Host 'Kaynaklar: pypi.org, download.pytorch.org, github.com/resemble-ai, huggingface.co.'
    if ($SkipModels) { Write-Host 'Model indirmesi atlanacak; ses uretimi icin daha sonra modeller gerekli.' }
    if ((Read-Host 'Kuruluma baslamak icin E yazin') -ine 'E') { throw 'Kurulum iptal edildi.' }
    $python = Prepare-Venv '.venv' $basePython
    $sttPython = Prepare-Venv '.venv-stt' $basePython
    Initialize-Chatterbox
    Invoke-Checked $python @('-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel')
    Invoke-Checked $python @('-m', 'pip', 'install', 'torch==2.10.0', 'torchaudio==2.10.0', 'torchvision==0.25.0', '--index-url', "https://download.pytorch.org/whl/$index")
    Invoke-Checked $python @('-m', 'pip', 'install', '-r', 'requirements.txt')
    Invoke-Checked $python @('-m', 'pip', 'check')
    Invoke-Checked $python @('scripts\provision-runtime.py', 'check', '--device', $targetDevice)
    Invoke-Checked $sttPython @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-Checked $sttPython @('-m', 'pip', 'install', '-r', 'apps\backend\requirements-stt.txt')
    Invoke-Checked $sttPython @('-m', 'pip', 'check')
    Invoke-Checked $sttPython @('-c', 'import faster_whisper, ctranslate2; print(''Whisper kutuphaneleri hazir'')')
    if (-not $SkipModels) {
        Invoke-Checked $python @('scripts\provision-runtime.py', 'download')
        Invoke-Checked $sttPython @('scripts\download-stt.py')
        Invoke-Checked $python @('scripts\provision-runtime.py', 'smoke', '--device', $targetDevice)
        Invoke-Checked $sttPython @('scripts\provision-runtime.py', 'stt-check', '--device', $targetDevice)
    }
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'apps\frontend')
    try {
        Invoke-Checked npm.cmd @('ci')
        Invoke-Checked npm.cmd @('run', 'build')
    } finally { Pop-Location }
    $settingsArgs = @('scripts\provision-runtime.py', 'settings', '--device', $targetDevice)
    if ($SkipModels) { $settingsArgs += '--online' }
    Invoke-Checked $python $settingsArgs
    Write-Host "`nKurulum tamamlandi. Baslatmak icin: .\scripts\start-app.ps1"
    Write-Host 'Adres: http://127.0.0.1:8000'
    Write-Host 'Sohbet icin LM Studio API sunucusunu acin, ASYA Ayarlar ekranindan model secin.'
    Write-Host 'LM Studio indirme: https://lmstudio.ai/download'
    Write-Host 'Mevcut uygulama ayarlari varsa korundu; cihaz secimini Ayarlar ekranindan kontrol edin.'
}

# Dot-source for isolated tests; no interactive setup when loading functions.
if ($MyInvocation.InvocationName -ne '.') {
    Push-Location -LiteralPath $ProjectRoot
    try { Start-AsyaSetup; exit 0 }
    catch {
        Write-Host "`nHATA: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host 'DLL yukleme hatasi varsa Microsoft Visual C++ x64 Runtime:'
        Write-Host 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
        Write-Host 'CUDA/GPU hatasinda NVIDIA surucunuzu kontrol edin veya kurucuyu CPU secerek tekrar calistirin.'
        exit 1
    }
    finally { Pop-Location }
}
