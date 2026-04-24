---
type: memory_update_report
title: curation-uuidv7-resource-picker
summary: Recorded durable post-V1 hardening rules for UUIDv7 primary keys and admin console resource-picking UX.
tags:
  - curation
  - uuidv7
  - web-console
related_commit: 34840fd
status: active
---

# Memory Update Report

## Durable updates

- Updated `modules/milestone-1-control-plane-foundation.md` to record that control-plane primary keys must be generated through `adg.shared.ids.uuidv7()` and must not encode business names.
- Updated `modules/milestone-5-web-console.md` to record that admin tables should display human-readable resource labels and that policy/masking forms should use searchable resource selectors instead of manual `resource_id` entry.
- Updated `index.md` to add commit `34840fd` to the evidence base.

## Rejected candidates

- Did not create a separate runbook: the verification flow remains the standard full pytest, web build, and browser smoke test.
- Did not create a separate decision record: the UUIDv7 and resource-picker rules fit the existing module cards.

## Verification evidence

- `uv run --extra dev pytest` passed with 66 tests.
- `npm run build` passed for the web console.
- Browser smoke test verified masking resource selection and list display with `customers / warehouse.public.customers`.
