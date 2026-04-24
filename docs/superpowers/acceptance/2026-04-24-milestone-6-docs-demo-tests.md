# Acceptance Criteria: Milestone 6 Documentation, Demo, and Tests

**Spec:** `docs/superpowers/specs/2026-04-24-milestone-6-docs-demo-tests-design.md`
**Date:** 2026-04-24
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | README includes local quickstart for backend and web console. | Logic | README is opened. | Commands for seed, backend, web, tests, and build are present. |
| AC-002 | Demo seed creates usable control-plane data. | Logic | Seed script runs against a temporary SQLite URL. | Admin key, datasource, resource, field, tag, masking policy, and audit rows exist. |
| AC-003 | MCP client example demonstrates runtime tool calls. | Logic | Example file is opened. | It calls `list_datasources`, `list_resources`, and `describe_resource` using `X-ADG-API-Key`. |
| AC-004 | Docker demo files are present. | Logic | Repo root is inspected. | `Dockerfile` and `docker-compose.yml` exist with backend and web service definitions. |
| AC-005 | Final V1 verification passes. | API | Dependencies are installed. | Backend tests, ruff, mypy, web build, and browser click-through succeed. |
