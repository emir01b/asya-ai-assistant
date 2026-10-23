param([Parameter(Mandatory = $true)][string]$LanAddress)
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'HTTPS kurulumu PowerShell 7 gerektirir (pwsh).' }
Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop | Out-Null
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CertDir = Join-Path $ProjectRoot 'data\certs'
New-Item -ItemType Directory -Path $CertDir -Force | Out-Null
# Keys stay on the server and are readable only by this Windows user and SYSTEM.
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
& icacls.exe $CertDir /inheritance:r /grant:r "*$($Identity.User.Value):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Sertifika klasörü izinleri ayarlanamadı.' }
$RootPath = Join-Path $CertDir 'VoiceAIStudio-Local-CA.crt'
$RootKeyPath = Join-Path $CertDir 'root-key.dpapi'
$LeafPath = Join-Path $CertDir 'server.crt'
$LeafKeyPath = Join-Path $CertDir 'server.key'
$MetadataPath = Join-Path $CertDir 'server.json'
$RootKey = [Security.Cryptography.RSA]::Create(3072)
$LeafKey = $null
$RootCert = $null
$LeafCert = $null
try {
    if ((Test-Path -LiteralPath $RootPath) -and (Test-Path -LiteralPath $RootKeyPath)) {
        $PrivateKey = [Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($RootKeyPath), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        $ReadCount = 0
        $RootKey.ImportPkcs8PrivateKey($PrivateKey, [ref]$ReadCount)
        [Array]::Clear($PrivateKey, 0, $PrivateKey.Length)
        $PublicCert = [Security.Cryptography.X509Certificates.X509Certificate2]::CreateFromPem([IO.File]::ReadAllText($RootPath))
        $RootCert = [Security.Cryptography.X509Certificates.RSACertificateExtensions]::CopyWithPrivateKey($PublicCert, $RootKey)
        $PublicCert.Dispose()
    } else {
        $RootRequest = [Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=ASYA Local CA', $RootKey, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $RootRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true, $false, 0, $true))
        $RootRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new([Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyCertSign -bor [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::CrlSign, $true))
        $RootRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($RootRequest.PublicKey, $false))
        $RootCert = $RootRequest.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-10), [DateTimeOffset]::UtcNow.AddYears(5))
        [IO.File]::WriteAllText($RootPath, $RootCert.ExportCertificatePem())
        $PrivateKey = $RootKey.ExportPkcs8PrivateKey()
        $ProtectedKey = [Security.Cryptography.ProtectedData]::Protect($PrivateKey, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        [Array]::Clear($PrivateKey, 0, $PrivateKey.Length)
        [IO.File]::WriteAllBytes($RootKeyPath, $ProtectedKey)
    }
    if ($RootCert.NotAfter.ToUniversalTime() -lt [DateTime]::UtcNow.AddDays(365)) {
        throw 'Yerel CA sertifikasının geçerliliği yetersiz; CA yenileme ve istemci güven ayarı gerekiyor.'
    }
    $Reuse = $false
    if ((Test-Path -LiteralPath $MetadataPath) -and (Test-Path -LiteralPath $LeafPath) -and (Test-Path -LiteralPath $LeafKeyPath)) {
        $Metadata = Get-Content -LiteralPath $MetadataPath -Raw | ConvertFrom-Json
        $Reuse = $Metadata.address -eq $LanAddress -and ([DateTimeOffset]$Metadata.expires) -gt [DateTimeOffset]::UtcNow.AddDays(30)
    }
    if (-not $Reuse) {
        $LeafKey = [Security.Cryptography.RSA]::Create(2048)
        $Request = [Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=ASYA', $LeafKey, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $San = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
        foreach ($Address in @($LanAddress, '127.0.0.1', '::1')) { $San.AddIpAddress([ipaddress]::Parse($Address)) }
        $San.AddDnsName('localhost')
        $Request.CertificateExtensions.Add($San.Build())
        $Request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
        $Request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new([Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment, $true))
        $Usage = [Security.Cryptography.OidCollection]::new()
        $Usage.Add([Security.Cryptography.Oid]::new('1.3.6.1.5.5.7.3.1')) | Out-Null
        $Request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($Usage, $false))
        $Serial = [Security.Cryptography.RandomNumberGenerator]::GetBytes(16)
        $Serial[0] = $Serial[0] -band 127
        $Expires = [DateTimeOffset]::UtcNow.AddDays(365)
        $LeafCert = $Request.Create($RootCert, [DateTimeOffset]::UtcNow.AddMinutes(-5), $Expires, $Serial)
        [IO.File]::WriteAllText($LeafPath, $LeafCert.ExportCertificatePem())
        [IO.File]::WriteAllText($LeafKeyPath, $LeafKey.ExportPkcs8PrivateKeyPem())
        @{address=$LanAddress;expires=$Expires.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $MetadataPath -Encoding UTF8
    }
    $Fingerprint = $RootCert.GetCertHashString([Security.Cryptography.HashAlgorithmName]::SHA256)
    Write-Host "HTTPS sertifikası hazır. CA SHA256: $Fingerprint"
    Write-Host "Diğer cihaza yalnızca bu açık sertifika aktarılır: $RootPath"
} finally {
    if ($LeafCert) { $LeafCert.Dispose() }
    if ($RootCert) { $RootCert.Dispose() }
    if ($LeafKey) { $LeafKey.Dispose() }
    $RootKey.Dispose()
}
