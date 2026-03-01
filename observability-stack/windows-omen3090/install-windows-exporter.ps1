param(
    [string]$Version = "0.25.1",
    [int]$ListenPort = 9182,
    [string]$Collectors = "cpu,cs,logical_disk,net,os,service,system,textfile",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

if (-not $Force) {
    Assert-Admin
}

$arch = "amd64"
$msiName = "windows_exporter-$Version-$arch.msi"
$downloadUrl = "https://github.com/prometheus-community/windows_exporter/releases/download/v$Version/$msiName"
$tmpDir = Join-Path $env:TEMP "windows-exporter"
$msiPath = Join-Path $tmpDir $msiName

if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
}

Write-Host "Downloading $downloadUrl ..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $msiPath -UseBasicParsing

$collectorArg = $Collectors -replace ' ', ''

$textfileDir = 'C:\ProgramData\windows_exporter\textfile-collector'
if (-not (Test-Path $textfileDir)) {
    New-Item -ItemType Directory -Path $textfileDir -Force | Out-Null
}

$argumentList = @(
    '/i', "`"$msiPath`"",
    "ENABLECOLLECTORS=$collectorArg",
    "LISTEN_PORT=$ListenPort",
    "TEXTFILE_DIRECTORY=`"$textfileDir`"",
    '/qn',
    '/norestart'
)

Write-Host "Installing windows_exporter v$Version ..."
Start-Process msiexec.exe -ArgumentList $argumentList -Wait -NoNewWindow

Write-Host "Ensuring service is running..."
if (Get-Service -Name 'windows_exporter' -ErrorAction SilentlyContinue) {
    Restart-Service -Name 'windows_exporter'
} else {
    throw 'windows_exporter service not found after installation.'
}

$ruleName = "Prometheus Windows Exporter $ListenPort"
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -DisplayName $ruleName -Action Allow -Enabled True
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $ListenPort -Profile Any | Out-Null
}

Write-Host "windows_exporter is installed and listening on port $ListenPort."
Write-Host "Prometheus target: host.docker.internal:$ListenPort"
