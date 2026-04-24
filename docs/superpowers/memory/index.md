---
title: repository-memory-index
summary: Canonical memory for the implemented Milestone 1-6 V1 foundation.
status: active
---

# Repository Memory Index

## Covered now

- Implemented backend skeleton for the Milestone 1 control-plane foundation.
- Verified Milestone 1 scope around settings, FastAPI app wiring, control-plane persistence, API key auth, audit, and Alembic migrations.
- Stable auth and migration contracts hardened by review: admin routes require admin scope, expired keys are rejected, custom API key headers must work, and Alembic must honor `ADG_CONTROL_PLANE_DATABASE_URL`.
- Implemented Milestone 2 datasource CRUD, connector registry, relational metadata scanning, and control-plane resource snapshot persistence.
- Implemented Milestone 3 MCP-style runtime tools, SQL Guard, runtime policy checks, tag visibility, read-only connector execution, and runtime audit events.
- Implemented Milestone 4 masking policies, fixed/partial/hash/reversible masking, decrypt contexts, and internal decrypt API.
- Implemented Milestone 5 admin console APIs and the React + Ant Design web console.
- Implemented Milestone 6 V1 quickstart, demo seed data, Docker Compose packaging, MCP client example, and final demo-path verification.
- Post-V1 hardening commit `34840fd` standardized new control-plane primary keys on UUIDv7 and improved admin console resource association UX.

## Primary docs

- [Planned Backend Skeleton Module Card](modules/planned-backend-skeleton.md)
- [Milestone 1 Control Plane Foundation Module Card](modules/milestone-1-control-plane-foundation.md)
- [Milestone 2 Datasource Foundation Module Card](modules/milestone-2-datasource-foundation.md)
- [Milestone 3 MCP Runtime Module Card](modules/milestone-3-mcp-runtime.md)
- [Milestone 4 Masking and Decryption Module Card](modules/milestone-4-masking-decryption.md)
- [Milestone 5 Web Console Module Card](modules/milestone-5-web-console.md)
- [Milestone 6 Docs Demo Tests Module Card](modules/milestone-6-docs-demo-tests.md)
- [API Key Identity Context Contract](contracts/api-key-identity-context.md)

## Evidence base

- `docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md`
- `docs/superpowers/specs/2026-04-24-milestone-2-datasource-foundation-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-2-datasource-foundation.md`
- `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-3-mcp-runtime.md`
- `docs/superpowers/specs/2026-04-24-milestone-4-masking-decryption-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-4-masking-decryption.md`
- `docs/superpowers/specs/2026-04-24-milestone-5-web-console-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-5-web-console.md`
- `docs/superpowers/specs/2026-04-24-milestone-6-docs-demo-tests-design.md`
- `docs/superpowers/plans/2026-04-24-milestone-6-docs-demo-tests.md`
- Implementation range `a4e6392..2b70103`
- Review-hardening commits `5fe1c2a` and `2b70103`
- Milestone 2 implementation commit `910c534`
- Milestone 3 implementation commit `f9b49a3`
- Milestone 4 implementation commit `64aa10c`
- Milestone 5 implementation commit `d3eaeab`
- Milestone 6 implementation range `288432c..c1ba4dd`
- UUIDv7/resource-picker hardening commit `34840fd`

## Major gaps

- The Milestone 3 HTTP facade is MCP-style tool dispatch; full MCP protocol transport and client examples remain future work.
- The V1 demo includes an HTTP MCP-style client example, not a full MCP transport server.
- No separate decision, runbook, or lesson doc was added in this pass because the durable knowledge fit the existing module and contract docs.
