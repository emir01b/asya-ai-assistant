param([Parameter(Mandatory = $true)][string]$LanAddress, [ValidateSet(8000,8443)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$RuleName = "VoiceAIStudio-LAN-$Port"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ResultPath = Join-Path $ProjectRoot "data\logs\lan-firewall-$Port.json"
New-Item -ItemType Directory -Path (Split-Path -Parent $ResultPath) -Force | Out-Null
$LanInterface = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop
$AddressBytes = ([ipaddress]::Parse($LanAddress)).GetAddressBytes()
if (-not ($AddressBytes[0] -eq 10 -or ($AddressBytes[0] -eq 172 -and $AddressBytes[1] -ge 16 -and $AddressBytes[1] -le 31) -or ($AddressBytes[0] -eq 192 -and $AddressBytes[1] -eq 168))) {
    throw 'Bu bilgisayardaki özel bir IPv4 adresini kullanın.'
}
$ExistingRule = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
if ($ExistingRule -and $ExistingRule.Enabled -eq 'True' -and $ExistingRule.Action -eq 'Allow' -and $ExistingRule.Direction -eq 'Inbound') {
    $AddressFilter = $ExistingRule | Get-NetFirewallAddressFilter
    $PortFilter = $ExistingRule | Get-NetFirewallPortFilter
    if ($AddressFilter.LocalAddress -contains $LanAddress -and $AddressFilter.RemoteAddress -contains 'LocalSubnet' -and $PortFilter.LocalPort -eq "$Port" -and $PortFilter.Protocol -eq 'TCP') {
        Write-Host 'Yerel ağ güvenlik duvarı kuralı hazır.'
        return
    }
}
$Principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Yalnızca TCP $Port / yerel alt ağ kuralını eklemek için Windows yönetici izni gerekiyor."
    $ShellExe = (Get-Process -Id $PID).Path
    $ElevatedProcess = Start-Process -FilePath $ShellExe -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-LanAddress', $LanAddress, '-Port', $Port) -PassThru -Wait
    if ($ElevatedProcess.ExitCode -ne 0) { throw "Güvenlik duvarı kurulamadı. Ayrıntı: $ResultPath" }
    return
}
try {
    if ($ExistingRule) { $ExistingRule | Remove-NetFirewallRule }
    New-NetFirewallRule -Name $RuleName -DisplayName "ASYA - Yerel ağ (TCP $Port)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -LocalAddress $LanAddress -RemoteAddress LocalSubnet -InterfaceAlias $LanInterface.InterfaceAlias -Profile Any -EdgeTraversalPolicy Block | Out-Null
    @{success=$true;address=$LanAddress;port=$Port;remote='LocalSubnet'} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
} catch {
    @{success=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
    throw
}
