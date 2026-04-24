# Acceptance Criteria: Milestone 3 MCP Runtime

**Spec:** `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md`
**Date:** 2026-04-24
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | Runtime tool calls require a valid API key but do not require admin scope. | API | A non-admin active API key exists and `POST /mcp/tools/list_datasources` receives identity context. | The response status is 200 and includes visible datasources for the tenant. |
| AC-002 | Unsupported runtime tool names are rejected deterministically. | API | A valid API key exists. | `POST /mcp/tools/not_a_tool` returns 404 with detail `Unknown MCP tool`. |
| AC-003 | Datasource listing is tenant-scoped and excludes inactive datasources. | Logic | Active and inactive datasources exist across two tenants. | `list_datasources` returns only active datasources for the identity tenant. |
| AC-004 | Tags are visible only when attached to resources visible to the identity. | Logic | Two tags exist, but only one is attached to an allowed resource. | `list_tags` returns only the tag attached to the allowed resource. |
| AC-005 | Resource discovery and tag-based discovery apply resource policies. | Logic | A denied resource and an allowed resource exist under one datasource. | `list_resources` and `list_resources_by_tag` omit the denied resource. |
| AC-006 | Resource description returns fields with access decisions. | Logic | A resource has two fields and an active deny field policy for one field. | `describe_resource` returns both fields and marks the denied field access as `denied`. |
| AC-007 | SQL Guard accepts one read-only SELECT and injects a limit when missing. | Logic | Guard is called with `select id from public.customers`. | Result is allowed and normalized SQL contains `LIMIT 100`. |
| AC-008 | SQL Guard rejects mutations, multiple statements, and non-whitelisted functions. | Logic | Guard is called with unsafe SQL variants. | Result is not allowed and includes deterministic rejection reasons. |
| AC-009 | `execute_query` rejects SQL that accesses resources outside declared `resource_ids`. | Logic | A query references a known table not present in declared scope. | Runtime returns a rejected result and records a `sql_rejected` or `permission_rejected` audit event. |
| AC-010 | `execute_query` executes allowed read-only SQL through the connector and audits success. | Logic | A fake connector returns rows for a declared, allowed resource. | Runtime returns status `success`, rows, columns, query id, and a `query_execution` audit event. |
| AC-011 | `preview_resource` executes a bounded preview for relational tables and views. | Logic | A fake connector is registered and a relation resource exists. | Runtime returns at most the requested limit and records a metadata/query audit event. |
| AC-012 | Baseline migrations create tags and policy tables. | API | Alembic migrations run against an empty SQLite database. | Tables `tags`, `resource_tags`, `resource_policies`, and `field_policies` exist. |
