---
type: module_card
title: milestone-5-web-console
summary: Implemented admin console APIs and a React + Ant Design web console for V1 management workflows.
tags:
  - milestone-5
  - web-console
  - admin-api
related_docs:
  - docs/superpowers/specs/2026-04-24-milestone-5-web-console-design.md
  - docs/superpowers/acceptance/2026-04-24-milestone-5-web-console.md
  - docs/superpowers/plans/2026-04-24-milestone-5-web-console.md
last_verified_commit: d3eaeab
status: active
---

# Milestone 5 Web Console

## Responsibilities

- Provide admin APIs for resource browsing, tags, policies, masking policies, API keys, audit logs, and MCP setup metadata.
- Provide a Vite React TypeScript console under `web/`.
- Use Ant Design tables, forms, drawers, tabs, descriptions, and notifications for management workflows.
- Keep the first screen as a working control console rather than a landing page.

## Entry points

- Console admin router: `src/adg/admin_api/console.py`
- App router wiring: `src/adg/app/main.py`
- Web app: `web/src/main.tsx`
- Web styles: `web/src/styles.css`
- Vite config: `web/vite.config.ts`

## Invariants

- Console admin APIs require `require_admin_api_key`.
- Runtime side effects from MCP HTTP tool calls must commit at the route layer.
- The web console stores the operator-supplied API key in local storage and sends it through `X-ADG-API-Key`.
- `web/dist/`, `web/node_modules/`, `web/tsconfig.tsbuildinfo`, and runtime `data/` are local artifacts and must remain ignored.

## Extension points

- Milestone 6 can add quickstart/demo instructions that seed an admin key and run the backend plus Vite console.
- The web console can later split pages into modules as it grows; V1 keeps the implementation compact.

## Common pitfalls

- Treating the console as standalone without backend seed data. The UI expects a valid admin API key and live FastAPI admin endpoints.
- Committing web build artifacts or local SQLite/log files.
- Reintroducing password-input browser warnings for the API key field.
