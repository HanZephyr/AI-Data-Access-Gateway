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
last_verified_commit: 9b0b509
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
- Production web proxy: `web/nginx.conf`
- Web dependency lockfile: `web/package-lock.json`

## Invariants

- Console admin APIs require `require_admin_api_key`.
- Runtime side effects from MCP HTTP tool calls must commit at the route layer.
- The web console stores the operator-supplied API key in local storage and sends it through `X-ADG-API-Key`.
- Management tables should prioritize human-readable labels such as `resource_label` over raw primary/foreign key values. Raw UUIDs remain available in details when needed for troubleshooting.
- Policy and masking forms should use searchable resource selectors backed by `/admin/resources` rather than asking operators to copy `resource_id` strings manually.
- Production Nginx and the local Vite dev server must both proxy the current runtime HTTP tool entrypoint `/api/tools/` to the backend; local Vite uses the `/api/tools` proxy key.
- `web/package-lock.json` tarball `resolved` URLs should remain canonical `https://registry.npmjs.org/` URLs so Docker builds can keep `NPM_REGISTRY_URL` as an install-time registry override instead of baking a mirror into the lockfile.
- `web/dist/`, `web/node_modules/`, `web/tsconfig.tsbuildinfo`, and runtime `data/` are local artifacts and must remain ignored.

## Extension points

- Milestone 6 can add quickstart/demo instructions that seed an admin key and run the backend plus Vite console.
- The web console can later split pages into modules as it grows; V1 keeps the implementation compact.

## Common pitfalls

- Treating the console as standalone without backend seed data. The UI expects a valid admin API key and live FastAPI admin endpoints.
- Proxying `/mcp` but forgetting `/api/tools/`. The setup UI exposes both FastMCP `/mcp` and direct HTTP tool URLs, and the latter must work behind the same frontend origin in production and local development.
- Rewriting `web/package-lock.json` `resolved` fields to a private or regional registry. That conflicts with the configurable `NPM_REGISTRY_URL` build contract and creates noisy lockfile churn.
- Reintroducing manual foreign-key text boxes for resource association. This raises operator error risk and contradicts the console UX contract.
- Committing web build artifacts or local SQLite/log files.
- Reintroducing password-input browser warnings for the API key field.
