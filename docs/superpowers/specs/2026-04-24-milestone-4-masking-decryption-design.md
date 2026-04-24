# Milestone 4 Masking and Decryption Design

**Date:** 2026-04-24
**Status:** Approved

---

## Scope

Milestone 4 adds masking policies, fixed/partial/hash/reversible masking, decrypt contexts, the internal decrypt API, and masking/decrypt audit events. It builds on Milestone 3 by applying masking after connector execution and before runtime responses are returned.

This milestone remains backend-only. Admin CRUD for masking policies and web-console management pages are left for Milestone 5.

## Data Model

Add baseline control-plane tables:

- `masking_policies`
- `decrypt_contexts`

Masking policies match resource id, field name, optional subject, strategy, config, and status. Decrypt contexts store query id, user id, datasource id, encrypted temporary key, allowed fields JSON, expiry, and creation time.

## Masking

Supported strategies:

- `fixed`: replace the value with a configured replacement, default `***`
- `partial`: preserve configured prefix and suffix lengths and fill the middle
- `hash`: return deterministic SHA-256 hex using the service secret as salt
- `reversible`: encrypt the value with a query-level temporary Fernet key and return `$adg_rev$<context_id>$<ciphertext>`

Masking applies only to columns present in connector result rows and only when a matching active policy exists for the identity. The runtime response includes `masking.masked_columns`.

## Decryption

`POST /internal/decrypt` accepts:

```json
{
  "user_id": "user-1",
  "values": ["$adg_rev$ctx_1$ciphertext"]
}
```

It validates API key, marker format, decrypt context existence, user, and TTL. It decrypts the stored query key with a service key derived from `Settings.secret_key`, then decrypts each value. Expired contexts are rejected.

## Audit

Runtime masking writes masking audit metadata in the query execution event. Internal decrypt writes one `decryption` audit event per request.

## Testing

Tests cover masking strategies, reversible marker/decrypt flow, expired context rejection, runtime masking integration, internal decrypt API behavior, and migration table creation.
