---
type: module_card
title: milestone-6-docs-demo-tests
summary: Implemented V1 demo seed data, quickstart docs, Docker Compose packaging, MCP HTTP client example, and final demo quality gates.
tags:
  - milestone-6
  - docs
  - demo
  - verification
related_docs:
  - docs/superpowers/specs/2026-04-24-milestone-6-docs-demo-tests-design.md
  - docs/superpowers/acceptance/2026-04-24-milestone-6-docs-demo-tests.md
  - docs/superpowers/plans/2026-04-24-milestone-6-docs-demo-tests.md
last_verified_commit: c1ba4dd
status: active
---

# Milestone 6 Docs Demo Tests

## Responsibilities

- Provide `examples/seed_demo.py` to create console-ready demo data with an admin API key, datasource, resource, tag, masking policy, and audit event.
- Provide `examples/mcp_client_http.py` as the minimal HTTP client for the V1 MCP-style tool facade.
- Document local V1 quickstart steps in `README.md`.
- Package the backend demo path with `Dockerfile` and `docker-compose.yml`.
- Keep final V1 quality gates explicit: pytest, ruff, mypy, web build, seed script, and browser console click-through.

## Entry points

- Demo seeding: `examples/seed_demo.py`
- MCP HTTP client: `examples/mcp_client_http.py`
- Backend container: `Dockerfile`
- Local compose stack: `docker-compose.yml`
- Quickstart: `README.md`

## Invariants

- Demo seed output must include the usable admin API key, currently `adg_admin`.
- Demo seed should be idempotent enough for repeated quickstart runs against the same SQLite database.
- Runtime-generated `data/` files remain ignored and must not be committed.
- Import `Base` from `adg.control_plane.models.base` in scripts that only need metadata. Importing through `adg.control_plane.models` can trigger package-level model imports too early.

## Extension points

- Add a true MCP transport adapter when the project moves beyond the V1 HTTP facade.
- Add richer seed profiles for policy and masking demos.
- Add an automated browser test harness once the console workflow stabilizes further.

## Common pitfalls

- Running the web console without seeding demo data and an admin key first.
- Starting Vite against a backend using a different SQLite database than the seed script.
- Reintroducing circular imports by exporting audit models from `adg.control_plane.models.__init__`.
