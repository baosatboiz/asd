param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

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
    Push-Location "$root\eureka"
    .\mvnw.cmd -q -DskipTests clean package
    Pop-Location

    Push-Location "$root\api-gateway"
    .\mvnw.cmd -q -DskipTests clean package
    Pop-Location

    Push-Location "$root\user-service"
    .\mvnw.cmd -q -DskipTests clean package
    Pop-Location
}

Start-ServiceProcess -Name "Eureka" -WorkingDirectory "$root\eureka" -Arguments ".\mvnw.cmd spring-boot:run"
Start-ServiceProcess -Name "Gateway" -WorkingDirectory "$root\api-gateway" -Arguments ".\mvnw.cmd spring-boot:run"
Start-ServiceProcess -Name "User service A" -WorkingDirectory "$root\user-service" -Arguments ".\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=a"
Start-ServiceProcess -Name "User service B" -WorkingDirectory "$root\user-service" -Arguments ".\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=b"

Write-Host ""
Write-Host "Services launching..."
Write-Host "Eureka dashboard: http://localhost:8761"
Write-Host "Gateway endpoint: http://localhost:8080/api/whoami"
Write-Host "Metrics: http://localhost:8080/actuator/prometheus"
Write-Host ""
Write-Host "To add instance C:"
Write-Host "  cd '$root\user-service'"
Write-Host "  .\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=c"
# mvn spring-boot:run -Dspring-boot.run.profiles=dev
# java -jar target/user-service-0.0.1-SNAPSHOT.jar --spring.profiles.active=c --spring.main.lazy-initialization=true -XX:TieredStopAtLevel=1