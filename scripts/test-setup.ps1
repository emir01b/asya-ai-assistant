# Offline installer regression tests; no packages downloaded or installed.
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $RepoRoot 'kurulum.ps1')
$FixtureParent = Join-Path $RepoRoot '.setup-tests'
$TestRoot = Join-Path $FixtureParent ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $TestRoot | Out-Null
# Explicit fixture roots below avoid any dependency on PowerShell dynamic scope.
if ((Split-Path -Parent $TestRoot) -ne $FixtureParent -or $TestRoot -eq $RepoRoot) { throw 'Unsafe fixture root' }
$script:Passed = 0

function Assert-True($Condition, [string]$Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
}
function Expect-Error([scriptblock]$Action, [string]$Pattern) {
    $caught = $false
    try { & $Action | Out-Null } catch {
        if ($_.Exception.Message -notmatch $Pattern) { throw }
        $caught = $true
    }
    Assert-True $caught "Expected error: $Pattern"
    $script:Passed++
}

try {
    Expect-Error { Find-Python311 (Join-Path $TestRoot 'missing.exe') } 'https://www.python.org/ftp/python/3.11.9/'
    # User data must survive cancellation and backup.
    $old = Join-Path $TestRoot '.venv'
    New-Item -ItemType Directory -Path $old | Out-Null
    Set-Content -LiteralPath (Join-Path $old 'keep.txt') -Value 'preserve me'
    function Read-Host { param($Prompt); return '' }
    Expect-Error { Prepare-Venv '.venv' 'unused.exe' -EnvironmentRoot $TestRoot } 'iptal'
    Assert-True ((Get-Content (Join-Path $old 'keep.txt')) -eq 'preserve me') 'Cancellation modified environment'
    # Mock only the venv creation command, preserving real filesystem behavior.
    function Invoke-Checked {
        param([string]$Exe, [string[]]$Arguments)
        Assert-True ($Arguments[0] -eq '-m' -and $Arguments[1] -eq 'venv') 'Unexpected installer command'
        New-Item -ItemType Directory -Path (Join-Path $Arguments[2] 'Scripts') | Out-Null
        Set-Content -LiteralPath (Join-Path $Arguments[2] 'Scripts\python.exe') -Value 'test placeholder'
    }
    function Read-Host { param($Prompt); return 'Y' }
    $createdPython = Prepare-Venv '.venv' 'unused.exe' -EnvironmentRoot $TestRoot
    Assert-True ($createdPython -eq (Join-Path $old 'Scripts\python.exe')) 'venv return value polluted by command output'
    $backups = @(Get-ChildItem -LiteralPath $TestRoot -Directory -Filter '.venv.backup-*')
    Assert-True ($backups.Count -eq 1) 'Backup missing'
    Assert-True ((Get-Content (Join-Path $backups[0].FullName 'keep.txt')) -eq 'preserve me') 'Backup contents changed'
    $script:Passed++
    # A junction must never update or rename the shared target.
    $shared = Join-Path $TestRoot 'shared-runtime'
    New-Item -ItemType Directory -Path $shared | Out-Null
    Set-Content -LiteralPath (Join-Path $shared 'keep.txt') -Value 'shared data'
    New-Item -ItemType Junction -Path (Join-Path $TestRoot '.venv-stt') -Target $shared | Out-Null
    Expect-Error { Prepare-Venv '.venv-stt' 'unused.exe' -EnvironmentRoot $TestRoot } 'junction/sembolik'
    Assert-True ((Get-Content (Join-Path $shared 'keep.txt')) -eq 'shared data') 'Shared target changed'
    # Occupied port is a hard gate before any installation.
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8000)
    try {
        $listener.Start()
        Expect-Error { Assert-ServerStopped } 'Port 8000 kullanimda'
    } catch [System.Net.Sockets.SocketException] {
        # If ASYA itself owns this port, the same guard must still reject it.
        Expect-Error { Assert-ServerStopped } 'Port 8000 kullanimda'
    } finally { $listener.Stop() }
    Write-Host "PASS: $script:Passed installer regression checks"
} finally {
    # Never follow a junction during recursive cleanup.
    $junctionPath = Join-Path $TestRoot '.venv-stt'
    if (Test-Path -LiteralPath $junctionPath) { [IO.Directory]::Delete($junctionPath) }
    $tempPrefix = [IO.Path]::GetFullPath($FixtureParent).TrimEnd('\') + '\'
    $resolvedTestRoot = [IO.Path]::GetFullPath($TestRoot)
    if (-not $resolvedTestRoot.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Leaf $resolvedTestRoot) -notmatch '^[a-f0-9]{32}$') { throw 'Unsafe test cleanup path' }
    Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
}
