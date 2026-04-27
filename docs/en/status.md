# Project Status

## Release Positioning

AI Data Access Gateway is currently released as a V1 MVP. The repository is strong enough for local evaluation, guided demos, and iterative open-source collaboration, but it is not yet positioned as an enterprise-ready production control plane.

## Implemented Today

### Backend

- FastAPI application factory with admin, runtime, internal decrypt, health, FastMCP Streamable HTTP mounted at `/mcp`, and a simpler HTTP tool API at `/api/tools/{tool_name}`
- SQLAlchemy control-plane models and Alembic migrations
- API key issuance, validation, scope checks, expiry handling, and one-time bootstrap/admin onboarding flow
- Relational datasource registration plus connector adapters for PostgreSQL, MySQL-compatible systems, and Doris
- Metadata scan and resource snapshot persistence for datasource catalogs

### Runtime and governance

- Runtime identity derived from bound API keys instead of caller-supplied identity fields
- Directory-backed users, roles, org nodes, and role assignment flows
- Read-only runtime tool execution protected by SQL Guard validation
- Resource and field policy enforcement
- Fixed, partial, hash, and reversible masking strategies with decrypt-context support
- Internal decrypt API for trusted callers with the proper scope
- Audit logging for metadata discovery, query execution, masking/decrypt activity, and admin operations
- Directory import flows from Excel and pluggable pull-only connector scaffolding for Feishu, WeCom, and DingTalk

### Admin console

- React + Vite console with onboarding for admin key entry
- Pages for datasources, resources, policies, masking policies, users, roles, audit logs, and MCP setup guidance
- In-browser admin workflows that avoid persisting the admin API key across reloads

### Packaging and demo flow

- Local demo seed script that creates a console-ready datasource, resource, masking policy, audit event, and one-time admin key
- Example HTTP client flow plus admin MCP setup metadata for the Streamable HTTP endpoint at `/mcp` and the simpler tool route at `/api/tools/{tool_name}`
- Docker Compose packaging with a backend container plus a built frontend served through Nginx
- Release verification includes frontend production audit plus Python dependency audit against an exported frozen dependency snapshot

## Known Limitations

- Admin access is still API-key-based only; there is no separate admin identity system, SSO, MFA, or session layer.
- Policies currently gate datasource, resource, and field access, but they do not enforce row-level security or query rewriting.
- The repository ships a local-friendly SQLite default and a demo-oriented Compose stack rather than a hardened production deployment blueprint.
- The current runtime and MCP surfaces are served from the main FastAPI process, so operators still need to layer their own perimeter, TLS termination, and deployment controls around it.

## Explicitly Out Of Scope For The Current MVP

- Enterprise multi-admin governance with approval chains or admin RBAC
- Full production deployment hardening, HA topology, and managed secret rotation integrations
- Row-level policy enforcement, policy simulation, or automatic SQL rewriting
- Claims of zero-trust production readiness

## Near-Term Hardening Priorities

- Keep release-facing CI, dependency audit, and documentation verification workflows running against the repository's resolved Python dependency graph and production frontend dependency set.
- Strengthen admin authentication posture beyond long-lived API keys alone.
- Improve deployment guidance, observability, backup, and recovery documentation for non-demo environments.
