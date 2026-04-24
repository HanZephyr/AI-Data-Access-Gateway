# Acceptance Criteria: Milestone 2 Datasource Foundation

**Spec:** `docs/superpowers/specs/2026-04-24-milestone-2-datasource-foundation-design.md`
**Date:** 2026-04-24
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | Admin-scoped API keys can create a datasource record. | API | Gateway app is running with an active admin API key. | `POST /admin/datasources` returns `201` and a datasource payload containing `id`, `name`, `type`, `datasource_kind`, `status`, `created_at`, and `updated_at`. |
| AC-002 | Admin-scoped API keys can list datasource records. | API | At least one datasource exists. | `GET /admin/datasources` returns `200` and includes the created datasource record. |
| AC-003 | Admin-scoped API keys can fetch a datasource by id. | API | A datasource exists. | `GET /admin/datasources/{id}` returns `200` with the matching datasource payload. |
| AC-004 | Admin-scoped API keys can update mutable datasource fields. | API | A datasource exists. | `PATCH /admin/datasources/{id}` returns `200` and reflects the updated `name`, `config_json`, and `status` values. |
| AC-005 | Deleting a datasource removes the datasource and its snapshot rows. | API | A datasource exists with scanned resources and fields. | `DELETE /admin/datasources/{id}` returns `204`; subsequent datasource lookup returns `404`; related `resources` and `resource_fields` rows no longer exist. |
| AC-006 | Unknown datasource ids return a deterministic not-found response. | API | No datasource exists for the requested id. | `GET`, `PATCH`, `DELETE`, `POST /test`, and `POST /scan` return `404` with a stable error detail for the missing datasource. |
| AC-007 | Connector registry resolves supported connector types. | Logic | Registry is initialized. | Looking up `postgres`, `mysql`, and `doris` returns the expected connector classes without raising an exception. |
| AC-008 | Unsupported connector types fail with a stable domain error. | Logic | Registry is initialized. | Looking up an unknown connector type raises a gateway domain error whose message identifies the unsupported connector type. |
| AC-009 | Missing optional connector drivers fail with a clear installation hint. | Logic | The adapter is exercised in an environment where the optional driver import is unavailable. | `test_connection` or `scan_metadata` raises a connector-not-installed error that names the required extra. |
| AC-010 | Connector test endpoint reports success for a reachable datasource. | API | A datasource exists and its connector test stub succeeds. | `POST /admin/datasources/{id}/test` returns `200` with `{ "status": "ok" }`. |
| AC-011 | Scan endpoint persists normalized resource snapshots. | API | A datasource exists and its connector scan stub returns relational metadata. | `POST /admin/datasources/{id}/scan` returns `200` with deterministic resource and field counts, and the database contains matching `resources` and `resource_fields` rows. |
| AC-012 | Re-running scan replaces old snapshot rows for the datasource. | API | A datasource already has scanned rows, and a second scan returns different metadata. | After the second scan, stale rows from the first scan are absent and only the second snapshot remains. |
| AC-013 | Resource snapshots classify relational objects with stable kinds. | Logic | A relational metadata snapshot is persisted. | Databases are stored as `database`, schemas as `schema`, tables as `relational_table`, and views as `relational_view`. |
| AC-014 | New migrations create datasource and snapshot tables. | API | A clean SQLite control-plane database is migrated with Alembic. | The migrated schema contains `datasources`, `resources`, and `resource_fields` in addition to prior Milestone 1 tables. |
