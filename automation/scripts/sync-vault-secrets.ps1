[CmdletBinding()]
param(
    [string]$VaultAddr = $env:VAULT_ADDR,
    [string]$VaultToken = $env:VAULT_TOKEN,
    [string]$SecretsMount = 'kv',
    [string]$RuntimeSecret = 'zeroclaw',
    [string]$AutomationSecret = 'automation',
    [string]$SecureStackEnvPath,
    [string[]]$TerraformArgs,
    [string]$TerraformWorkingDir,
    [string]$AppRolePath = 'approle',
    [string]$RoleIdFile,
    [string]$SecretIdFile,
    [switch]$UseAppRole,
    [string]$AutomationVaultToken = $env:VAULT_AUTOMATION_TOKEN,
    [string]$AutomationRoleIdFile,
    [string]$AutomationSecretIdFile,
    [switch]$UseAutomationAppRole,
    [string]$AutomationAppRolePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-FullPath {
    param([string]$Path, [string]$Base)
    if (-not $Path) {
        throw 'Path parameter is required.'
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path -Path $Base -ChildPath $Path))
}

function Get-FileContentOrNull {
    param([string]$Path)
    if (-not $Path) { return $null }
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File not found: $Path"
    }
    return (Get-Content -LiteralPath $Path -ErrorAction Stop | Select-Object -First 1).Trim()
}

function Get-VaultTokenInternal {
    param(
        [string]$VaultAddr,
        [string]$VaultToken,
        [switch]$UseAppRole,
        [string]$RoleIdFile,
        [string]$SecretIdFile,
        [string]$AppRolePath
    )
    if ($VaultToken) {
        return $VaultToken
    }
    $shouldUseAppRole = $UseAppRole -or $RoleIdFile -or $SecretIdFile
    if ($shouldUseAppRole) {
        $roleId = Get-FileContentOrNull -Path $RoleIdFile
        $secretId = Get-FileContentOrNull -Path $SecretIdFile
        $loginBody = @{ role_id = $roleId; secret_id = $secretId } | ConvertTo-Json -Compress
        $uri = "{0}/v1/auth/{1}/login" -f $VaultAddr.TrimEnd('/'), $AppRolePath.Trim('/')
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body $loginBody -ContentType 'application/json'
        return $response.auth.client_token
    }
    $defaultTokenPath = Join-Path -Path $HOME -ChildPath '.vault-token'
    if (Test-Path -LiteralPath $defaultTokenPath) {
        return (Get-Content -LiteralPath $defaultTokenPath | Select-Object -First 1).Trim()
    }
    throw 'Vault token not provided. Set VAULT_TOKEN, pass -UseAppRole, or log in via `vault login`.'
}

function Get-VaultSecretData {
    param([string]$VaultAddr, [string]$Token, [string]$Mount, [string]$Name)
    $uri = "{0}/v1/{1}/data/{2}" -f $VaultAddr.TrimEnd('/'), $Mount.Trim('/'), $Name.Trim('/')
    $headers = @{ 'X-Vault-Token' = $Token }
    $response = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -ErrorAction Stop
    return $response.data.data
}

# Derive default paths if not provided
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SecureStackEnvPath) {
    $SecureStackEnvPath = Join-Path -Path $scriptRoot -ChildPath '..\..\zeroclaw\deploy\secure-stack\.env'
}
if (-not $TerraformWorkingDir) {
    $TerraformWorkingDir = Join-Path -Path $scriptRoot -ChildPath '..\terraform'
}
$SecureStackEnvPath = Resolve-FullPath -Path $SecureStackEnvPath -Base $scriptRoot
$TerraformWorkingDir = Resolve-FullPath -Path $TerraformWorkingDir -Base $scriptRoot

if (-not $VaultAddr) {
    throw 'Vault address not provided. Set VAULT_ADDR or pass -VaultAddr.'
}

if (-not $AutomationAppRolePath) {
    $AutomationAppRolePath = $AppRolePath
}

$token = Get-VaultTokenInternal -VaultAddr $VaultAddr -VaultToken $VaultToken -UseAppRole:$UseAppRole -RoleIdFile $RoleIdFile -SecretIdFile $SecretIdFile -AppRolePath $AppRolePath
$automationToken = $token
if ($AutomationVaultToken -or $UseAutomationAppRole -or $AutomationRoleIdFile -or $AutomationSecretIdFile) {
    $automationToken = Get-VaultTokenInternal -VaultAddr $VaultAddr -VaultToken $AutomationVaultToken -UseAppRole:$UseAutomationAppRole -RoleIdFile $AutomationRoleIdFile -SecretIdFile $AutomationSecretIdFile -AppRolePath $AutomationAppRolePath
}

$runtimeData = $null
try {
    $runtimeData = Get-VaultSecretData -VaultAddr $VaultAddr -Token $token -Mount $SecretsMount -Name $RuntimeSecret
} catch {
    Write-Warning "Runtime secret ${SecretsMount}/${RuntimeSecret} not found: $($_.Exception.Message)"
}

if ($runtimeData) {
    $envLines = @()
    foreach ($key in ($runtimeData.Keys | Sort-Object)) {
        $value = $runtimeData[$key]
        if ($null -ne $value) {
            $envLines += "$key=$value"
        }
    }
    $secureStackDir = Split-Path -Parent $SecureStackEnvPath
    if (-not (Test-Path -LiteralPath $secureStackDir)) {
        New-Item -ItemType Directory -Path $secureStackDir -Force | Out-Null
    }
    if ($envLines.Count -gt 0) {
        Set-Content -Path $SecureStackEnvPath -Value ($envLines -join [Environment]::NewLine) -Encoding UTF8
        Write-Host "Wrote secure stack env file: $SecureStackEnvPath"
    } else {
        Write-Warning 'Runtime secret returned no key/value pairs; skipped .env generation.'
    }
}

$automationData = $null
try {
    $automationData = Get-VaultSecretData -VaultAddr $VaultAddr -Token $automationToken -Mount $SecretsMount -Name $AutomationSecret
} catch {
    Write-Warning "Automation secret ${SecretsMount}/${AutomationSecret} not found: $($_.Exception.Message)"
}

if ($automationData -and $automationData.ContainsKey('tailscale_auth_key')) {
    $env:TF_VAR_tailscale_auth_key = $automationData['tailscale_auth_key']
    Write-Host 'TF_VAR_tailscale_auth_key exported for this PowerShell session.'
}

if ($TerraformArgs -and $TerraformArgs.Length -gt 0) {
    if (-not (Test-Path -LiteralPath $TerraformWorkingDir)) {
        throw "Terraform directory not found: $TerraformWorkingDir"
    }
    Push-Location -Path $TerraformWorkingDir
    try {
        & terraform @TerraformArgs
    } finally {
        Pop-Location
    }
}
