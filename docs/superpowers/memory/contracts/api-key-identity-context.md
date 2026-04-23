---
type: contract
title: api-key-identity-context
summary: Implemented Milestone 1 API key authentication contract with header configurability, expiry enforcement, and admin-scope gating.
tags:
  - auth
  - contract
related_docs:
  - docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md
  - docs/superpowers/plans/2026-04-24-milestone-1-project-skeleton.md
  - docs/superpowers/memory/modules/milestone-1-control-plane-foundation.md
last_verified_commit: 5fe1c2a
status: active
---

# API Key Identity Context Contract

## Scope

- Covers the implemented Milestone 1 API key authentication behavior in `adg.app.dependencies` and the admin-system route that consumes it.
- The design's broader "identity context" idea remains future work; the stable implemented surface in this worktree is API key authentication plus admin scope enforcement.

## Producers and consumers

- Producers: admin clients and other trusted callers that send the configured API key header.
- Consumer: the FastAPI gateway service through `require_api_key`.
- Downstream readers: admin route dependencies now, with policy checks, audit logging, and internal decrypt validation expected in later milestones.

## Interface rules

- Gateway authentication reads the header named by `Settings.api_key_header`; the default remains `X-ADG-API-Key`, but custom header names are part of the supported contract.
- A missing or empty API key header returns `401 Missing API key`.
- A non-matching API key returns `401 Invalid API key`.
- A matching key whose `expires_at` is in the past returns `401 Expired API key`, even if the row is still marked active.
- Admin routes such as `/admin/system` must require `require_admin_api_key`; a valid non-admin key returns `403 Admin scope required`.
- The authenticated dependency returns only API key id and serialized scopes in Milestone 1. Request-supplied identity context fields are not yet a stable consumed interface here.

## Invariants

- V1 does not include a login system, OAuth, or JWT-based identity.
- Identity context alone is not trusted.
- Admin authorization is additive to authentication, not a separate bypass path.
- Later authorization layers still narrow access in order: datasource, resource, field, then masking.

## Compatibility notes

- This contract was hardened by review fixes in `5fe1c2a`, which added stable tests for expired-key rejection, admin-scope enforcement, and custom header support.
- Do not assume all endpoints already accept the same identity payload shape; Milestone 1 has not yet turned the design's identity-context fields into verified endpoint contracts.
