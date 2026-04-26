# Acceptance Criteria: Runtime and Admin Security Hardening

**Spec:** `docs/superpowers/specs/2026-04-26-security-hardening-runtime-admin-design.md`
**Date:** 2026-04-26
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | Runtime SQL guard rejects `SELECT *` queries. | Logic | A runtime query string contains `select * from public.customers`. | Guard result is rejected with a wildcard-specific rejection reason and no normalized SQL. |
| AC-002 | Runtime SQL guard rejects qualified wildcard projections such as `table.*`. | Logic | A runtime query string contains `select c.*, c.id from public.customers c`. | Guard result is rejected with a wildcard-specific rejection reason and no normalized SQL. |
| AC-003 | Runtime query execution rejects any query that references a field denied by field policy. | Logic | A readable resource exists, the caller has resource-level read access, and the referenced field has a matching deny field policy. | `execute_query()` returns a rejected response and the connector query function is not called. |
| AC-004 | Runtime query execution rejects any query that references a disabled field. | Logic | A readable resource exists and a referenced `ResourceField.status` is not `active`. | `execute_query()` returns a rejected response with a field-disabled reason and the connector query function is not called. |
| AC-005 | Resource preview uses an explicit allowlisted select list instead of `SELECT *`. | Logic | A resource has multiple active fields and only a subset is field-readable for the caller. | `preview_resource()` emits SQL containing only allowed field names and no wildcard projection. |
| AC-006 | Resource preview rejects resources with zero readable active fields. | Logic | A resource exists but every active field is denied or disabled for the caller. | `preview_resource()` returns a rejected response and does not call the connector. |
| AC-007 | Persisted datasource secrets are encrypted before being stored in the control-plane database. | API | An admin creates or updates a datasource with a non-empty `password`. | The stored `config_json` does not contain the plaintext password and instead contains an encrypted secret envelope. |
| AC-008 | Admin datasource APIs do not return plaintext stored secrets. | API | A datasource with an encrypted persisted password exists. | List/get/create/update datasource responses omit the plaintext password and return a placeholder-safe secret representation only. |
| AC-009 | Datasource updates preserve the existing encrypted secret when the password field is omitted. | API | A datasource with an existing encrypted password is updated without a password field in the payload. | The stored encrypted password remains unchanged and the update succeeds. |
| AC-010 | Datasource updates preserve the existing encrypted secret when the submitted password normalizes to empty. | API | A datasource with an existing encrypted password is updated with an empty password input. | The stored encrypted password remains unchanged and the update succeeds. |
| AC-011 | Runtime connector execution decrypts persisted datasource secrets before use. | Logic | A datasource config contains an encrypted persisted password and runtime query execution reaches the connector. | The connector receives the original plaintext password in its runtime config while the database keeps only ciphertext. |
| AC-012 | The admin console no longer persists the admin API key in browser storage. | UI interaction | The operator signs in to the web console with a valid admin key. | `localStorage` and `sessionStorage` do not gain an `adg.apiKey` entry, and reloading the page returns the UI to the signed-out state. |
| AC-013 | Policy APIs and runtime models no longer expose or rely on `priority`. | API | Policy CRUD endpoints and runtime policy evaluation are exercised after migrations. | Policy request/response payloads contain no `priority` field, policy tables contain no `priority` column, and runtime evaluation still follows deny-before-allow semantics. |
| AC-014 | Audit list responses do not include raw SQL by default. | API | At least one successful runtime query audit event with stored raw SQL exists. | The default admin audit list response omits raw SQL text while still returning the other audit summary fields. |
| AC-015 | Raw SQL remains retrievable through a dedicated detail path and that read is itself audited. | API | A successful runtime query audit event exists and an admin requests its raw SQL detail. | The detail response contains the stored raw SQL, and a secondary audit event recording the SQL-view action is persisted. |
| AC-016 | Production settings require a dedicated credential encryption key and reject placeholder or missing values. | Logic | Application settings are loaded in production mode with a missing or placeholder credential-encryption key. | Settings validation fails with an explicit configuration error. |
