param(
    [switch]$Build,
    [switch]$Docker,
    [int]$Scale = 2
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

# ── Docker mode ────────────────────────────────────────────────────────────────
if ($Docker) {
    Set-Location $root

    if ($Build) {
        Write-Host "Building Docker images..."
        docker compose build --no-cache
    }

    Write-Host "Starting stack with $Scale user-service replica(s)..."
    docker compose up -d --scale user-service=$Scale

    Write-Host ""
    Write-Host "Stack is up. Scaling commands:"
    Write-Host "  Scale up:   docker compose up -d --scale user-service=4"
    Write-Host "  Scale down: docker compose up -d --scale user-service=1"
    Write-Host "  Stop all:   docker compose down"
    Write-Host ""
    Write-Host "Endpoints:"
    Write-Host "  Eureka dashboard : http://localhost:8761"
    Write-Host "  Gateway whoami   : http://localhost:8080/api/whoami"
    Write-Host "  Users seed data  : http://localhost:8080/api/users"
    Write-Host "  Metrics          : http://localhost:8080/actuator/prometheus"
    Write-Host ""
    Write-Host "Run load test:"
    Write-Host "  ./demo/load-test.ps1 -Count 30"
    return
}

# ── Local Maven mode (dev without Docker) ───────────────────────────────────
function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Arguments
    )
    Start-Process -FilePath "powershell" `
        -ArgumentList "-NoExit", "-Command", $Arguments `
        -WorkingDirectory $WorkingDirectory | Out-Null
    Write-Host "Started $Name"
}

if ($Build) {
    Write-Host "Building services..."
    Push-Location "$root\eureka";      .\mvnw.cmd -q -DskipTests clean package; Pop-Location
    Push-Location "$root\api-gateway"; .\mvnw.cmd -q -DskipTests clean package; Pop-Location
    Push-Location "$root\user-service"; .\mvnw.cmd -q -DskipTests clean package; Pop-Location
}

Start-ServiceProcess -Name "Eureka"         -WorkingDirectory "$root\eureka"        -Arguments ".\mvnw.cmd spring-boot:run"
Start-ServiceProcess -Name "Gateway"        -WorkingDirectory "$root\api-gateway"   -Arguments ".\mvnw.cmd spring-boot:run"
Start-ServiceProcess -Name "User service A" -WorkingDirectory "$root\user-service"  -Arguments ".\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=a"
Start-ServiceProcess -Name "User service B" -WorkingDirectory "$root\user-service"  -Arguments ".\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=b"

Write-Host ""
Write-Host "Services launching (local / Maven mode)..."
Write-Host "Eureka dashboard: http://localhost:8761"
Write-Host "Gateway endpoint: http://localhost:8080/api/whoami"
Write-Host ""
Write-Host "To add instance C:"
Write-Host "  cd '$root\user-service'"
Write-Host "  .\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=c"
Write-Host ""
Write-Host "Tip: use -Docker to run the full stack in containers instead."