param(
    [int]$Count = 30,
    [int]$DelayMs = 250,
    [string]$Url = "http://localhost:8080/api/whoami"
)

$ErrorActionPreference = "Stop"

$distribution = @{}   # friendly-name -> count
$hostMap      = @{}   # raw hostname   -> friendly-name
$serviceInfo  = @{}   # friendly-name -> metadata
$errors       = 0
$nextIndex    = 1

for ($i = 1; $i -le $Count; $i++) {
    try {
        $response = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 5
        $raw = if ($response.hostname) { $response.hostname } else { $response.instanceId }

        # Assign a stable friendly name on first sight
        if (-not $hostMap.ContainsKey($raw)) {
            $hostMap[$raw] = "user-service-$nextIndex"
            $nextIndex++
        }
        $friendly = $hostMap[$raw]

        if (-not $distribution.ContainsKey($friendly)) {
            $distribution[$friendly] = 0
        }
        $distribution[$friendly]++

        if (-not $serviceInfo.ContainsKey($friendly)) {
            $serviceInfo[$friendly] = [PSCustomObject]@{
                Friendly   = $friendly
                Service    = $response.serviceName
                Hostname   = $raw
                InstanceId = $response.instanceId
                Version    = $response.version
                Port       = $response.port
            }
        }

        Write-Host ("{0,3}: {1}  v={2}  port={3}" -f $i, $friendly, $response.version, $response.port)
    } catch {
        $errors++
        Write-Host ("{0,3}: ERROR -> {1}" -f $i, $_.Exception.Message)
    }

    Start-Sleep -Milliseconds $DelayMs
}

$replicas = $distribution.Count
Write-Host ""
Write-Host "=== Distribution summary ($replicas replica(s) hit, $errors error(s)) ==="
$distribution.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $pct = [math]::Round(($_.Value / $Count) * 100)
    $bar = '#' * [math]::Round($_.Value / $Count * 20)
    Write-Host ("  {0,-18} {1,3} requests ({2,3}%)  {3}" -f $_.Key, $_.Value, $pct, $bar)
}

if ($serviceInfo.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Service details ==="
    $serviceInfo.GetEnumerator() | Sort-Object Name | ForEach-Object {
        $info = $_.Value
        Write-Host ("  {0}: service={1}, version={2}, port={3}, host={4}" -f $info.Friendly, $info.Service, $info.Version, $info.Port, $info.Hostname)
        Write-Host ("     instanceId={0}" -f $info.InstanceId)
    }
}

if ($replicas -gt 1) {
    Write-Host ""
    Write-Host "Load balancing is working across $replicas instance(s)."
} else {
    Write-Host ""
    Write-Host "WARNING: All requests landed on a single instance. Scale with:"
    Write-Host "  docker compose up -d --scale user-service=3"
}
