---
title: repository-memory-index
summary: Canonical memory for the implemented Milestone 1-3 backend foundation.
status: active
---

# Repository Memory Index

## Covered now

- Implemented backend skeleton for the Milestone 1 control-plane foundation.
- Verified Milestone 1 scope around settings, FastAPI app wiring, control-plane persistence, API key auth, audit, and Alembic migrations.
- Stable auth and migration contracts hardened by review: admin routes require admin scope, expired keys are rejected, custom API key headers must work, and Alembic must honor `ADG_CONTROL_PLANE_DATABASE_URL`.
- Implemented Milestone 2 datasource CRUD, connector registry, relational metadata scanning, and control-plane resource snapshot persistence.
- Implemented Milestone 3 MCP-style runtime tools, SQL Guard, runtime policy checks, tag visibility, read-only connector execution, and runtime audit events.

## Primary docs

- [Planned Backend Skeleton Module Card](modules/planned-backend-skeleton.md)
- [Milestone 1 Control Plane Foundation Module Card](modules/milestone-1-control-plane-foundation.md)
- [Milestone 2 Datasource Foundation Module Card](modules/milestone-2-datasource-foundation.md)
- [Milestone 3 MCP Runtime Module Card](modules/milestone-3-mcp-runtime.md)
- [API Key Identity Context Contract](contracts/api-key-identity-context.md)

## Evidence base

- `docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md`
- `docs/superpowers/specs/2026-04-24-milestone-2-datasource-foundation-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-2-datasource-foundation.md`
- `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-3-mcp-runtime.md`
- Implementation range `a4e6392..2b70103`
- Review-hardening commits `5fe1c2a` and `2b70103`
- Milestone 2 implementation commit `910c534`
- Milestone 3 implementation commit `f9b49a3`

## Major gaps

- Masking, decrypt, and web-console interfaces still should not be treated as implemented.
- The Milestone 3 HTTP facade is MCP-style tool dispatch; full MCP protocol transport and client examples remain future work.
- No separate decision, runbook, or lesson doc was added in this pass because the durable knowledge fit the existing module and contract docs.
