# AGENTS.md — Universal Agent Instructions
# Compatible with: OpenAI Codex, Claude Code, Copilot Agent, Cursor Composer, etc.

## Identity

You are a software engineering assistant working on a microservices university assignment.
You help students build, debug, document, and deploy a multi-service application.
The project follows **Domain-Driven Design (DDD)** with **Saga Orchestration** for the checkout flow.
Refer to `docs/analysis-and-design-ddd.md` for the domain model and `docs/architecture.md` for system design decisions.

> **Two-tier context**: This file covers project-wide rules only. Each service has its own `AGENTS.md` with scope-specific domain rules, data model, and API contracts. Always read the service-level file when working inside a service directory.

## Project Architecture

```
frontend/                          → User interface (React + Vite)
gateway/                           → API Gateway / reverse proxy (Spring Cloud Gateway)
services/
  identity-service/                → [Identity & Access Context]
  product-service/                 → [Catalog Context]
  order-service/                   → [Order Management Context]
  inventory-service/               → [Inventory Management Context]
  payment-service/                 → [Payment Management Context]
  orchestration-service/           → [Saga Orchestration Context]
docs/
  api-specs/                       → OpenAPI 3.0 YAML specifications
  architecture.md                  → System architecture documentation
  analysis-and-design-ddd.md       → DDD analysis: bounded contexts, aggregates, events
docker-compose.yml                 → Container orchestration
.env.example                       → Environment variable template
```

### Bounded Context → Service Mapping

> Default ports — override via `.env` if needed.

| Bounded Context | Service | Data Ownership | Port |
|----------------|---------|----------------|------|
| Identity & Access | identity-service | users, tokens, blacklist | 8081 |
| Catalog | product-service | products, categories | 8082 |
| Order Management | order-service | orders, order_items, order_events | 8083 |
| Inventory Management | inventory-service | inventory_items, reservations, inventory_history | 8084 |
| Payment Management | payment-service | payments, payment_events | 8085 |
| Saga Orchestration | orchestration-service | process state, workflow variables | 8086 |

Each service owns its data exclusively. Do NOT access or replicate data belonging to another bounded context.

## Core Constraints

1. **Technology-agnostic**: Any language/framework is valid. Don't assume a specific stack unless you see it in the code.
2. **Docker-first**: All code runs inside Docker containers. Never suggest running directly on the host.
3. **Single command deploy**: `docker compose up --build` must start the entire system.
4. **Database per service**: Each bounded context owns its data. No shared databases.
5. **Gateway routing**: Frontend → Gateway → Services. Never bypass the gateway.
6. **Health checks**: Every service implements `GET /health` → `{"status": "ok"}`.
7. **Environment variables**: Use `.env` for config. Never hardcode secrets.
8. **OpenAPI specs**: All APIs documented in `docs/api-specs/` (OpenAPI 3.0 YAML).
9. **Idempotency**: State-changing operations in the checkout flow MUST be idempotent via `orderId` or an idempotency key. Check for existing results before processing.
10. **Saga Orchestration**: Checkout is a distributed transaction across Order, Inventory, and Payment. NEVER use 2PC. Use Saga orchestration with compensating actions. The cross-service flow is: Create Order (PENDING) → Reserve Inventory → Initiate Payment → Wait for Payment Result → on success: Confirm Inventory + Order CONFIRMED / on failure: Release Inventory + Order PAYMENT_FAILED.
11. **Bounded Context isolation**: When working inside a service, read only that service's `AGENTS.md`. Do not assume or depend on internal behavior of other services — communicate only via their public API contracts.

## Coding Standards

- Follow idiomatic conventions for the service's chosen language
- Include proper error handling with meaningful error messages
- Add input validation on all endpoints
- Use type safety where available (TypeScript, Python type hints, etc.)
- Keep functions small, focused, and well-named
- Comments explain "why", not "what"

### DDD Standards

Each core service SHOULD follow **Layered Architecture** aligned with its Bounded Context. Apply where appropriate — lightweight or utility services may use a simplified structure.

```
services/<service-name>/
└── src/
    ├── domain/           → Core business logic (entities, value objects, domain events, repository interfaces)
    │                       No framework dependencies. Pure business rules.
    │
    ├── application/      → Use cases / application services (orchestrates domain objects)
    │                       Depends on domain layer only. Contains DTOs, command/query handlers.
    │
    ├── infrastructure/   → Technical implementations (JPA repositories, messaging adapters, external API clients)
    │                       Implements interfaces defined in the domain layer.
    │
    └── interfaces/       → Entry points (REST controllers, message listeners, scheduled tasks)
                            Translates external requests into application-layer calls.
```

**Rules:**
- **Domain layer** should have ZERO dependencies on frameworks. For lightweight services, a simplified flat structure is acceptable.
- **Dependency direction**: interfaces → application → domain ← infrastructure.
- **Each Bounded Context** maps 1:1 to a deployable service with its own database.
- **Aggregate roots** are the only entry points for modifications within a Bounded Context.
- **Domain Events** use past tense naming (e.g., `OrderCreated`, `InventoryReserved`, `PaymentFailed`).
- **Value Objects** are immutable — no setters, equality by value.
- Refer to `docs/analysis-and-design-ddd.md` §2.3 for the full aggregate data model.

## When Creating/Modifying Services

1. Read the service's own `AGENTS.md` first for scope-specific rules
2. Check `docs/api-specs/` for existing API contracts
3. Check `docs/analysis-and-design-ddd.md` for the domain model and aggregate structure
4. Implement/update the `GET /health` endpoint
5. Use Docker Compose service names for inter-service calls (e.g., `http://identity-service:8081`)
6. Update the OpenAPI spec when adding/changing endpoints
7. Update the service's `readme.md`
8. Verify the Dockerfile builds correctly

## When Debugging

1. Check Docker logs: `docker compose logs <service-name>`
2. Verify network connectivity between services
3. Check environment variables are properly loaded
4. Verify port mappings in docker-compose.yml
5. Test health endpoints first

## File Conventions

| Purpose | Location | Format |
|---------|----------|--------|
| Project-wide agent rules | `.ai/AGENTS.md` | Markdown |
| Service-specific agent rules | `services/<service>/AGENTS.md` | Markdown |
| API specs | `docs/api-specs/<service>.yaml` | OpenAPI 3.0 |
| Architecture | `docs/architecture.md` | Markdown |
| DDD Analysis | `docs/analysis-and-design-ddd.md` | Markdown |
| Service docs | `<service>/readme.md` | Markdown |
| Env config | `.env.example` → `.env` | KEY=VALUE |
| Diagrams | `docs/asset/` | PNG/SVG/Mermaid |

## Response Format

- Be concise and actionable
- Show code changes with file paths
- Explain trade-offs when making design decisions
- Suggest next steps after completing a task
