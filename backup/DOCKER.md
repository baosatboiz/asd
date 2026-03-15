# Docker Guide

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)

## Build and Run All Services

From the workspace root:

```powershell
docker compose up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- Eureka on `http://localhost:8761`
- User Service on `http://localhost:8083`
- API Gateway on `http://localhost:8080`

Seeded data is initialized automatically at startup via `schema.sql` and `data.sql` in the user-service image.

Quick check:

```powershell
Invoke-RestMethod http://localhost:8083/users
```

## Stop the Stack

```powershell
docker compose down
```

## Rebuild Images Only

```powershell
docker compose build --no-cache
```

## Notes

- Service discovery inside Docker uses `http://eureka:8761/eureka`.
- Host access uses mapped ports above.
