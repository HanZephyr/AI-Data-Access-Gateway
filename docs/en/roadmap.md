# Roadmap

## Principles

- Current code, tests, and runnable configuration are the source of truth.
- Roadmap items are planning targets, not present capabilities.
- Version labels describe likely sequencing and scope, not guaranteed release dates.

## V1.0: Current MVP Baseline

The current repository already delivers the core V1 foundation: a FastAPI control plane, relational datasource registration and metadata scanning, read-only governed runtime access, API-key-based directory-backed identity, SQL Guard validation, masking and decrypt controls, audit logging, a React admin console, demo seed data, and Docker Compose packaging.

## V1.1: Open-Source And Documentation Hardening

This stage focuses on making the repository easier to adopt and safer to evaluate in public. Priority work includes release-quality English and Chinese documentation, contributor and security governance files, baseline GitHub CI, scheduled dependency audit workflows, and explicit disclosure of known audit gaps instead of optimistic claims.

## V1.2: Operational Hardening

The next operational pass should improve the production posture without pretending the system is already enterprise complete. Likely work includes stronger admin authentication, secret-handling and rotation improvements, better deployment documentation, clearer observability hooks, and more repeatable verification around backup, recovery, and environment configuration.

## V2.0: Enterprise Foundation

V2 should introduce the larger-team controls that are intentionally outside the MVP. That likely means a stronger admin authentication and authorization model, richer governance controls, better operational safety rails, and a more deliberate separation between demo-friendly defaults and production deployment expectations.

## V3.0: Ecosystem Expansion

Longer term, the project can expand into broader datasource coverage, better extension points, and richer runtime integration patterns. That may include more connectors, deeper import/sync workflows, fuller MCP ecosystem support, and cleaner ways to embed the gateway into larger AI platform deployments.
