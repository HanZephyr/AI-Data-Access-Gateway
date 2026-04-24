# Milestone 5 Web Console Design

**Date:** 2026-04-24
**Status:** Approved

---

## Scope

Milestone 5 adds the V1 web console and the remaining admin APIs needed for the console to manage the gateway. The console is an operational control surface, not a marketing site.

## Design Direction

Visual thesis: a quiet, high-density control room with crisp tables, restrained color, and strong status scanning. The first screen is the working console: navigation, system summary, and selected operational data.

Content plan: overview, datasources, resources, tags, access policies, field policies, masking policies, API keys, audit logs, and MCP setup.

Interaction thesis: fast tab/page switching, drawer-style edit/create workflows, and compact feedback states for loading, empty, and error conditions.

## Backend APIs

Add admin-only endpoints for:

- resources and fields browsing
- tag CRUD and resource tag binding
- resource policy CRUD
- field policy CRUD
- masking policy CRUD
- API key creation and revocation
- audit event query
- MCP setup metadata

Existing datasource APIs remain the datasource management surface.

## Frontend

Add `web/` as a Vite + React + TypeScript + Ant Design app. The console reads an API key from a local settings panel and calls the FastAPI admin endpoints. It uses Ant Design tables, forms, drawers, tabs, tags, and notifications rather than custom replacements.

## Testing

Backend tests cover admin API authorization and representative CRUD/query behavior. Frontend verification covers TypeScript build, production build, and browser click-through of the main navigation.
