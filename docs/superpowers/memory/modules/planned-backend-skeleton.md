---
type: module_card
title: planned-backend-skeleton
summary: Implemented top-level backend skeleton for the first runnable single-service gateway slice.
tags:
  - architecture
  - milestone-1
related_docs:
  - docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md
  - docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md
last_verified_commit: 2b70103
status: active
---

# Planned Backend Skeleton

## Responsibilities

- Preserve the V1 single-service boundary around a FastAPI application plus internal layered modules.
- Provide the concrete Milestone 1 packages that already exist on disk: `app`, `admin_api`, `control_plane`, `audit`, and `shared`.
- Keep later milestone packages such as `mcp`, `internal_api`, `gateway_runtime`, `connectors`, `policy`, `sql_guard`, and `masking` outside the current implementation boundary.

## Entry points

- Repository root: `src/adg/`
- Application entry package: `src/adg/app/`
- Admin API package: `src/adg/admin_api/`
- Control-plane package: `src/adg/control_plane/`
- Audit package: `src/adg/audit/`
- Shared helpers: `src/adg/shared/`

## Invariants

- V1 is a single FastAPI service exposing MCP, admin REST, and internal HTTP surfaces from one process.
- In the implemented Milestone 1 slice, `adg.app.main` wires health and admin routes, while auth logic stays in `adg.app.dependencies`.
- `control_plane` owns DB session setup, Alembic migration metadata, and API key ORM state.
- `audit` owns audit event persistence instead of embedding that write path inside route handlers.
- Connector abstractions should avoid assuming every future datasource is SQL.
- Naming should prefer `datasource`, `resource`, `entity`, and `field` outside SQL-specific modules.

## Extension points

- Later milestones may add MCP tools, relational connectors, SQL Guard, masking, decrypt flows, and the web console inside the approved module boundaries.
- The design explicitly keeps future split points open for a later MCP Runtime / Control Plane separation.
- The current skeleton already leaves room to add more routers and control-plane models without reshaping the package layout.

## Common pitfalls

- Treating planned modules that do not yet exist on disk as if they were implemented just because the top-level package map mentions them.
- Moving auth or audit behavior into admin route handlers instead of keeping those concerns in shared dependencies and services.
- Forgetting that migration wiring is part of the control-plane module contract, not a one-off developer script.
