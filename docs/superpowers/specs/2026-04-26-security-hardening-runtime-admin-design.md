# Runtime and Admin Security Hardening Design

**Date:** 2026-04-26
**Status:** Approved

---

## Scope

This design hardens five areas of the gateway:

1. Runtime SQL validation and field-level authorization.
2. Resource preview query construction.
3. Admin-console API-key handling in the browser.
4. Persisted datasource credential storage and admin API serialization.
5. Policy-model simplification and audit-log exposure of raw SQL.

The trust model for this milestone is a single administrator using the control-plane console directly. The console is not treated as a multi-operator system and will not grow its own user-management or RBAC layer in this change set.

## Goals

- Prevent runtime callers from reading denied or disabled columns through `SELECT *` or any other field-authorization gap.
- Remove persistent browser storage of the admin API key.
- Ensure persisted datasource secrets are not stored in plaintext in the control-plane database.
- Stop returning persisted secrets to the admin UI after create, list, get, or update operations.
- Simplify runtime policy resolution by removing the unused `priority` concept.
- Keep raw SQL for AI troubleshooting while reducing casual exposure in the admin UI.

## Non-Goals

- Build a separate admin authentication system.
- Encrypt non-secret datasource metadata fields.
- Persist third-party directory importer secrets; those requests remain transient and request-scoped.
- Rewrite caller SQL to remove denied columns. The gateway validates and rejects; it does not mutate user-authored SQL.

## Runtime Query Hardening

### Wildcard Rejection

The runtime query path must reject all wildcard projections:

- `SELECT * FROM ...`
- `SELECT schema.table.* FROM ...`
- wildcard projections nested inside larger select lists

`SqlGuard` remains the single parsing and normalization gate. It will add a stable rejection reason for wildcard selection and will not produce normalized SQL for wildcard queries.

### Field-Level Enforcement

`GatewayRuntimeService.execute_query()` must treat field policies as execution-time authorization, not just metadata for `describe_resource()`.

After `SqlGuard` returns the accessed resources and fields:

1. Resolve the actual resources in scope.
2. Reject the query if any referenced field is disabled in any resolved resource.
3. Reject the query if any referenced field fails `check_field_access(..., action="read")` for the runtime identity.
4. Execute the SQL only when every referenced field is active and allowed.

The rejection behavior is whole-query rejection. The runtime does not redact, drop, or rewrite disallowed columns.

### Preview Queries

`preview_resource()` may no longer emit `SELECT *`.

Preview must:

1. Load active fields for the resource in ordinal order.
2. Keep only fields whose field-level read access is allowed for the current identity.
3. Build an explicit select list from those field names.
4. Reuse the normal guarded execution path.

If a resource has no readable active fields, preview returns a permission rejection instead of issuing a query.

## Persisted Secret Storage

### Secrets Covered

Persisted datasource configs must encrypt at least these secret fields:

- relational datasource `password`

The design intentionally targets persisted datasource credentials first because those values are stored in the control-plane database today. Third-party directory importer secrets remain request-only inputs and are not written to the control-plane database in the current design.

### Crypto Service

Add a dedicated credential-encryption service responsible for:

- encrypting secret config values before persistence
- decrypting secret config values before connector use
- exposing helpers that distinguish secret placeholders from real secret updates

This service must use a dedicated application secret separate from the general-purpose runtime secret. A new setting will be introduced for credential encryption, and production validation must reject missing or placeholder values.

### Stored Shape

Datasource config remains JSON, but secret-valued entries are stored as encrypted envelopes rather than plaintext strings. The envelope must carry enough metadata to support future key rotation and format upgrades, at minimum:

- encryption marker/version
- ciphertext payload

Non-secret fields remain plain JSON values.

## Admin API and UI Secret Handling

### Backend Serialization

Admin datasource endpoints must stop returning plaintext secrets. Serialized datasource payloads should return secret-aware placeholders instead of actual values so the UI can render edit state without learning the stored secret.

The placeholder format should be deterministic and UI-friendly, but it must not reveal plaintext length or value.

### Update Semantics

Secret updates follow these rules:

- missing field: keep existing stored secret unchanged
- empty string after normalization: keep existing stored secret unchanged
- non-empty string: treat as a replacement, encrypt, and persist

This preserves the current editing flow where an administrator can update metadata without re-entering credentials.

### Frontend Behavior

The admin console should show datasource secret inputs as placeholder values only. When the operator focuses or edits the field, the placeholder disappears and the field becomes a normal password input for replacement.

The browser never receives the previously stored plaintext secret.

## Admin API Key Storage

The admin API key is stored in in-memory React state only.

- No `localStorage`
- No `sessionStorage`
- Refreshing the page clears authentication state
- Reopening the browser requires re-entry of the key

Because the current trust model is a single local administrator, this change is sufficient for this milestone and avoids adding a separate session service.

The static frontend should also add baseline browser hardening headers through Nginx:

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy`

## Policy Simplification

The `priority` field is removed from:

- resource policy model
- field policy model
- admin API request and response payloads
- web-console forms and tables
- tests and migrations

Runtime policy resolution stays simple and explicit:

- any matching deny rejects
- otherwise any matching allow allows
- otherwise reject

For field policies, if policies exist for a field and none match an allow for the caller, the field is denied.

## Raw SQL Audit Exposure

Raw SQL remains stored because AI-generated queries must be inspectable during incident review and prompt debugging.

The change is in exposure, not retention:

- audit list APIs and default UI tables should not return raw SQL by default
- raw SQL should move behind a dedicated detail/read path
- viewing raw SQL from the admin UI should create a secondary audit event

This keeps troubleshooting value while reducing routine exposure of sensitive literals.

## Data and Migration Changes

The migration set must:

- add credential-encryption support to persisted datasource configs without data loss
- remove `priority` columns from policy tables

Existing plaintext datasource secrets need an in-place migration path. The migration strategy should read each datasource config, wrap configured secret fields in the new encrypted envelope, and write the transformed JSON back before the application starts relying on the new reader behavior.

## Testing Strategy

Tests must cover:

- wildcard query rejection for `*` and `table.*`
- runtime rejection of denied fields
- runtime rejection of disabled fields
- preview generation with explicit allowed field lists only
- datasource secret encryption on create and update
- datasource secret non-disclosure in admin API responses
- keep-existing-secret behavior when update payload omits or blanks the secret
- successful connector execution after decrypting persisted credentials
- removal of `priority` from API payloads and persistence
- audit list behavior excluding raw SQL by default
- raw SQL detail access and secondary audit logging
- admin key no longer persisting across reloads in the UI state model
