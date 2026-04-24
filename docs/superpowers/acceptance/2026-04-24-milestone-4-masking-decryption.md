# Acceptance Criteria: Milestone 4 Masking and Decryption

**Spec:** `docs/superpowers/specs/2026-04-24-milestone-4-masking-decryption-design.md`
**Date:** 2026-04-24
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | Baseline migrations create masking and decrypt tables. | API | Alembic migrations run against an empty SQLite database. | Tables `masking_policies` and `decrypt_contexts` exist. |
| AC-002 | Fixed masking replaces non-null values with a configured replacement. | Logic | A masking policy uses strategy `fixed` and replacement `REDACTED`. | Runtime row value becomes `REDACTED`. |
| AC-003 | Partial masking preserves configured prefix and suffix characters. | Logic | A policy uses prefix 2 and suffix 2 on `alice@example.com`. | Masked value keeps `al` and `om` with fill characters between them. |
| AC-004 | Hash masking is deterministic and secret-salted. | Logic | The same value is masked twice with the same secret. | Both outputs match and are not the plaintext. |
| AC-005 | Reversible masking creates decrypt contexts and ADG markers. | Logic | A runtime query returns a reversible field. | Response value starts with `$adg_rev$`, and a matching decrypt context row exists. |
| AC-006 | Internal decrypt returns plaintext for valid reversible markers. | API | A valid API key and unexpired context exist for the tenant/user. | `POST /internal/decrypt` returns the original plaintext value. |
| AC-007 | Internal decrypt rejects expired contexts. | Logic | A decrypt context expiry is in the past. | Decrypt service raises a validation error and does not return plaintext. |
| AC-008 | Runtime query responses include masking metadata. | Logic | One or more columns are masked. | Response `masking.masked_columns` lists column names and strategies. |
| AC-009 | Decrypt requests are audited. | API | A valid decrypt request is processed. | An audit event with event type `decryption` and decision `allowed` exists. |
