# Milestone 6 Documentation, Demo, and Tests Design

**Date:** 2026-04-24
**Status:** Approved

---

## Scope

Milestone 6 completes V1 with practical documentation and demo assets: local quickstart, demo seed data, MCP client examples, Docker/Docker Compose files, and final verification.

## Deliverables

- README quickstart for backend, web console, demo seed, tests, and browser access.
- `examples/seed_demo.py` to initialize SQLite with admin key, datasource, resource, field, tag, masking policy, and audit event.
- `examples/mcp_client_http.py` to call the MCP-style HTTP facade.
- `Dockerfile` and `docker-compose.yml` for local demo startup.
- Tests covering the demo seed script.

## Testing

The demo seed test runs against a temporary SQLite database and verifies the expected admin key, datasource, resource, and audit rows exist. Final V1 verification runs backend tests, ruff, mypy, frontend build, and browser click-through.
