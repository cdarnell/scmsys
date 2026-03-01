[CmdletBinding()]
param(
    [string]$StackPath = (Join-Path $PSScriptRoot '..\..\zeroclaw\deploy\secure-stack'),
    [string]$ClientName = 'automation-script',
    [string]$ClientContact = 'ops@local',
    [string]$ClientNotes = '',
    [string]$TokenOutFile,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-ComposeCommand {
    param(
        [string[]]$ComposeArgs
    )

    if ($VerbosePreference -ne 'SilentlyContinue') {
        Write-Verbose "docker compose args: $($ComposeArgs -join ' ')"
    }

    $output = & docker compose --ansi never @ComposeArgs 2>&1
    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        throw "docker compose $($Args -join ' ') failed with exit code $exit`n$output"
    }
    return ,$output
}

function Convert-LastJsonLine {
    param(
        [string[]]$Lines
    )
    $expandedLines = foreach ($line in $Lines) {
        if ($null -eq $line) {
            continue
        }
        $line -split '\r?\n'
    }

    $sanitizedLines = $expandedLines |
        ForEach-Object { $_ -replace '\x1b\[[0-9;]*m', '' }

    if ($VerbosePreference -ne 'SilentlyContinue') {
        Write-Verbose "Captured command output:`n$($sanitizedLines -join "`n")"
    }

    $jsonLine = $sanitizedLines |
        Where-Object { $_ -match '^\s*[\{\[]' } |
        Select-Object -Last 1
    if (-not $jsonLine) {
        throw 'Expected JSON payload in command output but none was found.'
    }
    return $jsonLine | ConvertFrom-Json
}

$resolvedStack = (Resolve-Path -Path $StackPath).ProviderPath
Push-Location -Path $resolvedStack
try {
    Write-Verbose "Working directory: $resolvedStack"

    $healthLines = Invoke-ComposeCommand -ComposeArgs 'exec', 'gateway', 'curl', '-sSf', 'http://127.0.0.1:3000/health'
    $health = Convert-LastJsonLine -Lines $healthLines

    if ($health.paired -and -not $Force.IsPresent) {
        Write-Host 'Gateway already has at least one paired client. Use -Force to request another token.'
        return
    }

    # If already paired but Force requested, warn user the gateway must be reset for new code.
    if ($health.paired -and $Force.IsPresent) {
        Write-Warning 'Gateway already paired. A fresh pairing code will only exist after you delete paired tokens from config.'
    }

    $logLines = Invoke-ComposeCommand -ComposeArgs 'logs', '--tail=400', 'gateway'
    $match = $logLines |
        Select-String -Pattern 'X-Pairing-Code:\s*(?<code>\d{6})' |
        Select-Object -Last 1

    if (-not $match) {
        throw 'Could not locate a pairing code in recent gateway logs. Make sure the gateway just restarted and is waiting for its first client.'
    }

    $pairingCode = $match.Matches[0].Groups['code'].Value
    Write-Host "Using pairing code: $pairingCode"

    $payload = [ordered]@{
        client        = $ClientName
        contact       = $ClientContact
        notes         = $ClientNotes
        requested_by  = $env:USERNAME
        requested_from = $env:COMPUTERNAME
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    # Remove empty values to keep payload tidy
    foreach ($key in @($payload.Keys)) {
        if (-not $payload[$key]) {
            [void]$payload.Remove($key)
        }
    }
    $payloadJson = ($payload | ConvertTo-Json -Depth 3 -Compress)

    $pairLines = Invoke-ComposeCommand -ComposeArgs 'exec', 'gateway', 'curl', '-sS', '-X', 'POST', 'http://127.0.0.1:3000/pair', '-H', "X-Pairing-Code: $pairingCode", '-H', 'Content-Type: application/json', '-d', $payloadJson
    $pairResponse = Convert-LastJsonLine -Lines $pairLines

    $token = $null
    if ($pairResponse.PSObject.Properties['bearer_token']) {
        $token = $pairResponse.bearer_token
    } elseif ($pairResponse.PSObject.Properties['token']) {
        $token = $pairResponse.token
    }
    if (-not $token) {
        throw 'Gateway response did not include a bearer_token/token field.'
    }
    Write-Host "New bearer token issued:" -ForegroundColor Green
    Write-Host $token

    if ($TokenOutFile) {
        try {
            $tokenPath = (Resolve-Path -Path $TokenOutFile -ErrorAction Stop).ProviderPath
        } catch {
            $parent = Split-Path -Path $TokenOutFile -Parent
            if ([string]::IsNullOrWhiteSpace($parent)) {
                $parent = (Get-Location).ProviderPath
            }
            if (-not (Test-Path -Path $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            $resolvedParent = (Resolve-Path -Path $parent).ProviderPath
            $tokenPath = Join-Path -Path $resolvedParent -ChildPath (Split-Path -Path $TokenOutFile -Leaf)
        }
        Set-Content -Path $tokenPath -Value $token -Encoding UTF8
        Write-Host "Token written to $tokenPath"
    }

    Write-Host 'Update your client config with this token (Authorization: Bearer ...).'
}
finally {
    Pop-Location
}
