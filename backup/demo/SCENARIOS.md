# Service Discovery Demo Scenarios

## Quick start

1. Open PowerShell in workspace root.
2. Run `./demo/run-demo.ps1 -Build` once, then `./demo/run-demo.ps1` for next runs.
3. After startup, run `./demo/load-test.ps1 -Count 20`.

## Scenario 1: Baseline load balancing

Command:

```powershell
./demo/load-test.ps1 -Count 30
```

Expected:
- Responses alternate between `:8083` and `:8084`.
- Eureka shows two `UP` instances for `USER-SERVICE`.

## Scenario 2: Scale out to instance C

Start new instance:

```powershell
cd ./user-service
./mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=c
```

Then:

```powershell
cd ..
./demo/load-test.ps1 -Count 40
```

Expected:
- `:8085` appears in responses after registration/fetch interval.

## Scenario 3: Graceful shutdown

Stop instance B (Ctrl+C in the 8084 terminal), then run:

```powershell
./demo/load-test.ps1 -Count 25
```

Expected:
- Traffic shifts to remaining healthy instances.
- Eureka no longer lists 8084 as `UP`.

## Scenario 4: Crash and eviction delay

Kill instance A process abruptly (close its terminal), then run:

```powershell
./demo/load-test.ps1 -Count 30 -DelayMs 200
```

Expected:
- Brief errors may appear while registry state converges.
- After eviction, errors drop and traffic stabilizes.

## Scenario 5: Health DOWN without process death

Mark instance C unhealthy directly:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8085/admin/health/down
./demo/load-test.ps1 -Count 30
```

Restore:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8085/admin/health/up
```

Expected:
- 8085 remains running but should disappear from gateway selection once Eureka reflects health.

## Risk scenario: Registry outage

1. Keep user-service instances and gateway running.
2. Stop Eureka server.
3. Continue `./demo/load-test.ps1 -Count 20`.
4. Start/stop a service instance while Eureka is down.

Expected:
- Some traffic may continue via cached registry data.
- New topology changes are not discovered until Eureka returns.

## Evidence to show

- Eureka dashboard: `http://localhost:8761`
- Gateway actuator: `http://localhost:8080/actuator/health`
- Gateway metrics: `http://localhost:8080/actuator/prometheus`
- Service health: `http://localhost:<port>/actuator/health`
- Service identity endpoint: `http://localhost:<port>/whoami`
