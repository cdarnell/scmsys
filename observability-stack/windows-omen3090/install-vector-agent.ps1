param(
    [string]$VectorVersion = "0.42.0",
    [string]$Hostname = "omen3090",
    [string]$AggregatorHost = "host.docker.internal",
    [int]$AggregatorPort = 6000,
    [string[]]$EventChannels = @("Application", "System"),
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

$msiName = "vector-$VectorVersion-x86_64.msi"
$downloadUrl = "https://packages.timber.io/vector/$VectorVersion/vector-x86_64-pc-windows-msvc.msi"
$tmpDir = Join-Path $env:TEMP "vector-installer"
$msiPath = Join-Path $tmpDir $msiName

if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
}

Write-Host "Downloading Vector $VectorVersion ..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $msiPath -UseBasicParsing

$msiArgs = @(
    '/i', "`"$msiPath`"",
    '/qn',
    '/norestart'
)

Write-Host "Installing Vector service ..."
Start-Process msiexec.exe -ArgumentList $msiArgs -Wait -NoNewWindow

$configDir = "C:\\ProgramData\\Vector\\config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$channelsToml = ($EventChannels | ForEach-Object { '"{0}"' -f $_ }) -join ", "
$configContent = @"
data_dir = "C:/ProgramData/Vector/data"

[sources.host_metrics]
type = "host_metrics"
scrape_interval_secs = 15
collectors = ["cpu", "filesystem", "memory", "network", "system", "processes"]

[transforms.host_metrics_tagged]
type = "remap"
inputs = ["host_metrics"]
source = '''
if .tags == null {
  .tags = {}
}
.tags.host = "${Hostname}"
'''

[sources.windows_events]
type = "windows_events"
channels = [${channelsToml}]

[transforms.windows_event_labels]
type = "remap"
inputs = ["windows_events"]
source = '''
level_val = "Information"
channel_val = "Application"
if exists(.record) && exists(.record.LevelDisplayName) {
  level_val = to_string!(.record.LevelDisplayName)
} else if exists(.level) {
  level_val = to_string!(.level)
}
if exists(.record) && exists(.record.Channel) {
  channel_val = to_string!(.record.Channel)
} else if exists(.channel) {
  channel_val = to_string!(.channel)
}
.level = level_val
.channel = channel_val
'''

[transforms.windows_event_metrics]
type = "log_to_metric"
inputs = ["windows_event_labels"]
metrics = [
  { type = "counter", name = "windows_event_logs_total", field = "message", tags = { channel = "{{channel}}", level = "{{level}}", host = "${Hostname}" } },
  { type = "counter", name = "windows_event_errors_total", field = "message", tags = { channel = "{{channel}}", host = "${Hostname}" }, condition = ".level == \"Error\" || .level == \"Critical\"" }
]

[sinks.aggregate]
type = "vector"
inputs = ["host_metrics_tagged", "windows_event_metrics"]
address = "${AggregatorHost}:${AggregatorPort}"
version = "2"
healthcheck.enabled = true
"@

$configPath = Join-Path $configDir "windows-agent.toml"
Set-Content -Path $configPath -Value $configContent -Encoding UTF8
$defaultConfig = Join-Path $configDir "vector.toml"
Copy-Item -Path $configPath -Destination $defaultConfig -Force

if (Get-Service -Name 'vector' -ErrorAction SilentlyContinue) {
    Restart-Service -Name 'vector'
} else {
    Start-Service -Name 'vector'
}

Write-Host "Vector agent installed and streaming metrics to ${AggregatorHost}:${AggregatorPort}."
Write-Host "Config path: $configPath"
