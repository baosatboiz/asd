param(
    [int]$Count = 30,
    [int]$DelayMs = 250,
    [string]$Url = "http://localhost:8080/api/whoami"
)

$ErrorActionPreference = "Stop"

$distribution = @{}

for ($i = 1; $i -le $Count; $i++) {
    try {
        $response = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 3
        $instance = "$($response.instanceId)@$($response.port)"

        if (-not $distribution.ContainsKey($instance)) {
            $distribution[$instance] = 0
        }
        $distribution[$instance]++

        Write-Host ("{0,3}: {1} ({2})" -f $i, $instance, $response.version)
    } catch {
        Write-Host ("{0,3}: ERROR -> {1}" -f $i, $_.Exception.Message)
    }

    Start-Sleep -Milliseconds $DelayMs
}

Write-Host ""
Write-Host "Distribution summary"
$distribution.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("  {0} -> {1} requests" -f $_.Key, $_.Value)
}
