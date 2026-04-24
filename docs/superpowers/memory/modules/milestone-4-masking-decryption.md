---
type: module_card
title: milestone-4-masking-decryption
summary: Implemented masking policies, runtime masking, decrypt contexts, and internal decrypt API.
tags:
  - milestone-4
  - masking
  - decrypt
related_docs:
  - docs/superpowers/specs/2026-04-24-milestone-4-masking-decryption-design.md
  - docs/superpowers/acceptance/2026-04-24-milestone-4-masking-decryption.md
  - docs/superpowers/plans/2026-04-24-milestone-4-masking-decryption.md
  - docs/superpowers/memory/modules/milestone-3-mcp-runtime.md
last_verified_commit: 64aa10c
status: active
---

# Milestone 4 Masking and Decryption

## Responsibilities

- Persist masking policies and decrypt contexts in the control-plane database.
- Apply fixed, partial, hash, and reversible masking after connector execution and before runtime responses.
- Return masking metadata through `execute_query` responses.
- Store reversible decrypt contexts and expose `POST /internal/decrypt` for trusted internal services.
- Audit successful decrypt requests and include masked column metadata in query execution audit payloads.

## Entry points

- Masking models: `src/adg/control_plane/models/masking.py`
- Masking service: `src/adg/masking/service.py`
- Runtime integration: `src/adg/gateway_runtime/tools.py`
- Internal decrypt router: `src/adg/internal_api/decrypt.py`
- Migration baseline: `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`

## Invariants

- Masking happens after SQL Guard, resource policy, and connector execution.
- Active masking policies match tenant, resource id, field name, optional subject, and strategy.
- `fixed`, `partial`, and `hash` masking never create decrypt contexts.
- `reversible` masking returns `$adg_rev$<context_id>$<ciphertext>` markers.
- Reversible value decryption validates tenant, user, context existence, and TTL before returning plaintext.
- Internal decrypt requires an API key with `internal` scope.
- HTTP routes that create audit events or decrypt contexts must commit their session so side effects survive beyond the request.

## Extension points

- Milestone 5 can add admin CRUD and web-console pages for masking policies.
- Future versions can replace the SQLite decrypt context store with Redis without changing runtime marker shape.
- Decrypt permission checks can be narrowed further once V1 adds explicit decrypt policies.

## Common pitfalls

- Forgetting to commit route-level runtime side effects. Service methods flush, but request handlers own persistence.
- Treating reversible markers as plaintext-safe without validating context TTL and identity.
- Applying masking before connector execution or before policy checks. Masking belongs at the final row shaping stage.
