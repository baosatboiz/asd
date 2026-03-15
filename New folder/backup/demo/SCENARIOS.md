# Service Discovery Demo Scenarios

## Quick start (Docker — recommended)

```powershell
# First time: build images and start with 2 replicas
./demo/run-demo.ps1 -Docker -Build -Scale 2

# Run load test
./demo/load-test.ps1 -Count 30
```

## Quick start (local Maven — no Docker)

```powershell
./demo/run-demo.ps1 -Build   # first time
./demo/run-demo.ps1          # subsequent runs
./demo/load-test.ps1 -Count 20
```

---

## Scenario 1: Baseline load balancing

```powershell
./demo/load-test.ps1 -Count 30
```

Expected:
- Load test summary shows requests spread across 2 hostnames.
- Eureka dashboard (`http://localhost:8761`) lists two `UP` instances for `USER-SERVICE`.

## Scenario 2: Scale out (add more replicas)

```powershell
# Add a third replica
docker compose up -d --scale user-service=3

# Wait ~10 s for registration, then test
./demo/load-test.ps1 -Count 40
```

Expected:
- A new hostname appears in the distribution table.
- Eureka shows three `UP` instances.

## Scenario 3: Scale down (graceful)

```powershell
docker compose up -d --scale user-service=1
./demo/load-test.ps1 -Count 25
```

Expected:
- Traffic converges to the single remaining instance.
- Eureka deregisters the stopped replicas.

## Scenario 4: Crash and eviction delay

Abruptly kill one replica:

```powershell
# Find a user-service container name
docker ps --filter name=user-service

# Kill it (replace <name> with actual container name)
docker kill <name>

./demo/load-test.ps1 -Count 30 -DelayMs 200
```

Expected:
- Brief errors while Eureka evicts the dead instance (up to `lease-expiration-duration-in-seconds` = 15 s).
- Errors stop once eviction completes.

## Scenario 5: Health DOWN without process death

Find a running container name, then exec the admin endpoint:

```powershell
# List containers
docker ps --filter name=user-service

# Mark one instance unhealthy via docker exec
docker exec <container_name> wget -qO- --post-data '' http://localhost:8083/admin/health/down

./demo/load-test.ps1 -Count 30

# Restore
docker exec <container_name> wget -qO- --post-data '' http://localhost:8083/admin/health/up
```

Expected:
- Unhealthy instance should disappear from gateway selection once Eureka reflects the health state.

## Scenario 6: Registry outage

1. Stop Eureka: `docker compose stop eureka`
2. Run: `./demo/load-test.ps1 -Count 20`
3. Scale while Eureka is down: `docker compose up -d --scale user-service=4`
4. Restart Eureka: `docker compose start eureka`

Expected:
- Some traffic continues via cached gateway registry entries.
- New replicas are only discovered after Eureka returns.

---

## Useful endpoints

| What | URL |
|---|---|
| Eureka dashboard | `http://localhost:8761` |
| Gateway health | `http://localhost:8080/actuator/health` |
| Gateway metrics | `http://localhost:8080/actuator/prometheus` |
| Identity (via gateway) | `http://localhost:8080/api/whoami` |
| Users seed data | `http://localhost:8080/api/users` |
