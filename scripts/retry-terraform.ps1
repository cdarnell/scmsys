param(
    [int]$Interval = 60,
    [int]$MaxAttempts = 0,
    [string]$TerraformDir = (Resolve-Path "$PSScriptRoot/../terraform").Path,
    [string]$LogFile = (Join-Path (Resolve-Path "$PSScriptRoot/../terraform").Path "last-apply.log")
)

Set-Location $TerraformDir

$attempt = 0
$maxLabel = if ($MaxAttempts -le 0) { '∞' } else { $MaxAttempts }
Write-Host "[info] Starting retry loop in $TerraformDir (interval ${Interval}s, max attempts ${maxLabel})."

while ($true) {
    $attempt++
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    Write-Host "[$timestamp] Attempt ${attempt}: terraform apply -auto-approve"

    terraform apply -auto-approve -input=false *>&1 | Tee-Object -FilePath $LogFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[success] Apply completed on attempt $attempt."
        break
    }

    Write-Warning "Apply failed (likely capacity). See $LogFile for details."
    if ($MaxAttempts -gt 0 -and $attempt -ge $MaxAttempts) {
        throw "Giving up after $attempt attempts."
    }
    Start-Sleep -Seconds $Interval
    Write-Host
}
