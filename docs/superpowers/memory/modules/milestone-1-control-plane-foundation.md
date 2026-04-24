---
type: module_card
title: milestone-1-control-plane-foundation
summary: Implemented Milestone 1 backend foundation around settings, control-plane storage, API key auth, admin health, audit, and migrations.
tags:
  - milestone-1
  - control-plane
related_docs:
  - docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md
  - docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md
  - docs/superpowers/memory/contracts/api-key-identity-context.md
last_verified_commit: 34840fd
status: active
---

# Milestone 1 Control Plane Foundation

## Responsibilities

- Establish the first runnable backend skeleton for the gateway.
- Provide settings loading, FastAPI app startup, control-plane persistence, Alembic migration wiring, API key validation, admin-system authorization, and audit event persistence.
- Keep Milestone 1 intentionally smaller than the full V1 design.

## Entry points

- App factory: `src/adg/app/main.py`
- Settings: `src/adg/app/settings.py`
- Auth dependencies: `src/adg/app/dependencies.py`
- Admin system router: `src/adg/admin_api/system.py`
- DB session layer: `src/adg/control_plane/db.py`
- Alembic environment: `src/adg/control_plane/migrations/env.py`
- ORM base and models: `src/adg/control_plane/models/`
- ID generator: `src/adg/shared/ids.py`
- Audit writer: `src/adg/audit/service.py`

## Invariants

- SQLite is the default control-plane database for V1 and Milestone 1.
- `ADG_CONTROL_PLANE_DATABASE_URL` is the control-plane DB authority for runtime and Alembic when explicitly set; migration wiring must not silently prefer `alembic.ini`.
- API key validation is part of the foundation before broader admin, MCP, or internal API growth.
- API key header lookup is driven by `Settings.api_key_header`, so custom header names must work anywhere `require_api_key` is used.
- Expired API keys must be rejected even when the stored key is otherwise valid and still marked active.
- Admin routes must depend on admin-scoped API keys rather than generic API key authentication.
- Audit is foundational in Milestone 1 even though most event types arrive in later milestones.
- Control-plane primary keys must be generated with `adg.shared.ids.uuidv7()`. Business names, paths, labels, and descriptions belong in their dedicated fields, not in primary-key strings.
- This milestone does not yet include connectors, metadata scanning, MCP runtime tools, policy evaluation, SQL Guard, masking, decrypt APIs, or the web console.

## Extension points

- Milestone 2 extends the control plane with datasource CRUD, metadata scanning, and resource snapshots.
- Later milestones add policy tables, masking policy tables, decrypt contexts, and richer audit usage.
- Additional admin routes should reuse the same dependency contract instead of open-coding scope checks.

## Common pitfalls

- Assuming Milestone 1 already defines the final control-plane schema. The current migration stabilizes the initial tables needed for API keys and audit, not later policy or metadata tables.
- Reading admin authorization as "any valid key may call admin routes." Review hardened this: admin scope is mandatory.
- Treating key expiration as an optional caller concern. The auth dependency owns expiry rejection.
- Updating Alembic config without checking the settings override path covered by `ADG_CONTROL_PLANE_DATABASE_URL`.
