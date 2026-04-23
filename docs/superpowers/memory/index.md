---
title: repository-memory-index
summary: Canonical memory for the implemented and review-hardened Milestone 1 control-plane foundation.
status: active
---

# Repository Memory Index

## Covered now

- Implemented backend skeleton for the Milestone 1 control-plane foundation.
- Verified Milestone 1 scope around settings, FastAPI app wiring, control-plane persistence, API key auth, audit, and Alembic migrations.
- Stable auth and migration contracts hardened by review: admin routes require admin scope, expired keys are rejected, custom API key headers must work, and Alembic must honor `ADG_CONTROL_PLANE_DATABASE_URL`.

## Primary docs

- [Planned Backend Skeleton Module Card](modules/planned-backend-skeleton.md)
- [Milestone 1 Control Plane Foundation Module Card](modules/milestone-1-control-plane-foundation.md)
- [API Key Identity Context Contract](contracts/api-key-identity-context.md)

## Evidence base

- `docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md`
- Implementation range `a4e6392..2b70103`
- Review-hardening commits `5fe1c2a` and `2b70103`

## Major gaps

- Connector, MCP runtime, policy, masking, decrypt, and web-console interfaces still should not be treated as implemented.
- The current canonical contracts are concentrated in control-plane bootstrap, API key auth, and admin-system health surface; broader request schemas remain future work.
- No separate decision, runbook, or lesson doc was added in this pass because the durable review findings fit the existing module and contract docs.
