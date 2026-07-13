---
type: module_card
title: milestone-3-mcp-runtime
summary: Implemented MCP-style runtime tools, conservative SQL Guard, runtime policies, tag visibility, read-only connector execution, and audit events.
tags:
  - milestone-3
  - runtime
  - sql-guard
  - policy
related_docs:
  - docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md
  - docs/superpowers/acceptance/2026-04-24-milestone-3-mcp-runtime.md
  - docs/superpowers/plans/2026-04-24-milestone-3-mcp-runtime.md
  - docs/superpowers/specs/2026-07-13-mcp-api-key-authentication-design.md
  - docs/superpowers/acceptance/2026-07-13-mcp-api-key-authentication.md
  - docs/superpowers/plans/2026-07-13-mcp-api-key-authentication.md
  - docs/superpowers/memory/modules/milestone-2-datasource-foundation.md
last_verified_commit: f2b9767
status: active
---

# Milestone 3 MCP Runtime

## Responsibilities

- Provide transport-neutral runtime tool handlers for datasource, tag, resource, preview, and query workflows.
- Expose FastMCP Streamable HTTP at `/mcp` as the primary AI-agent entrypoint and a supplemental authenticated plain HTTP tool API at `POST /api/tools/{tool_name}` for traditional service integrations.
- Enforce runtime resource and field policies over Milestone 2 resource snapshots.
- Parse SQL through a conservative AST-based guard before read-only connector execution.
- Record runtime audit events for discovery, successful execution, connector failures, SQL rejection, and permission rejection.

## Entry points

- Runtime service: `src/adg/gateway_runtime/tools.py`
- FastAPI mount and `/mcp` path normalization: `src/adg/app/main.py`
- FastMCP Streamable HTTP server: `src/adg/mcp_server/server.py`
- Supplemental plain HTTP tool API: `src/adg/mcp_api/tools.py`
- Policy service: `src/adg/policy/runtime.py`
- SQL Guard: `src/adg/sql_guard/guard.py`
- Governance models: `src/adg/control_plane/models/governance.py`
- Query connector contract: `src/adg/connectors/base.py`
- Relational query execution: `src/adg/connectors/relational.py`
- Runtime datasource engine cache: `src/adg/connectors/runtime_engine_cache.py`

## Invariants

- Runtime tool calls use runtime API key authentication, not `require_admin_api_key`; admin scope is not required for MCP or direct HTTP tool callers.
- `/mcp` accepts the configured API Key Header (default `X-ADG-API-Key`), `apikey` query parameter, or `Authorization: Bearer <key>` as the same runtime API Key. Every non-empty value across all sources, including repeated Header values, must match; conflicting values return HTTP 400 before database authentication. Query and Bearer inputs do not extend to `/api/tools/{tool_name}`.
- Runtime identity comes from the authenticated API key's bound user. Tool request payloads must not be trusted for `user_id`, `roles`, or `groups`; direct HTTP tool dispatch rejects those fields.
- Runtime policy evaluation defaults to allow only when no active policies exist for the requested action.
- When active policies exist for an action, matching allow is required and matching deny wins.
- Field policies only narrow access after parent resource access has been granted.
- SQL Guard accepts only one `SELECT`/`WITH` style read-only statement and rejects mutation, DDL, transaction, multi-statement, and non-whitelisted function use.
- SQL resources extracted from SQL must map to known resource snapshots. Unknown or ambiguous SQL resources must be rejected before connector execution.
- Declared `resource_ids` are an intent scope; actual SQL resource extraction remains authoritative.
- Runtime relational queries reuse process-local SQLAlchemy engines through an LRU/idle-TTL cache only after policy and SQL Guard checks have passed.
- Runtime datasource pool settings must be exposed through both application settings and Docker Compose backend environment variables; Compose `.env` values are not injected into containers unless explicitly mapped.
- Runtime datasource timeout settings are DBAPI connection arguments for relational runtime queries: PostgreSQL receives `connect_timeout`, while MySQL/Doris receive `connect_timeout`, `read_timeout`, and `write_timeout`.
- Connector dependency or execution failures after SQL and policy checks return structured `status: "error"` responses with `error.type` and `error.message`, and must not include empty `rows`, `columns`, or `masking` result fields.
- Connector failures are audited with `decision="error"`, the normalized SQL, the generated `query_id`, the actual resource ids, and metadata containing `error_type` and `error_message`.

## Extension points

- A later MCP transport should call `GatewayRuntimeService` and shared runtime dispatch rather than duplicate tool authorization logic.
- Milestone 4 masking should attach after policy checks and before rows are returned.
- Milestone 5 web console can manage the governance tables added here.
- Additional connector types can implement the shared `execute_query` contract without changing runtime tool dispatch.
- Query timeout settings should not be treated as query cancellation, retries, or engine-cache eviction logic.

## Common pitfalls

- Treating historical `POST /mcp/tools/{tool_name}` as a current runtime entrypoint or compatibility alias. It is obsolete and intentionally unsupported; AI agents should use FastMCP Streamable HTTP `/mcp`, while non-agent traditional services may use the supplemental `POST /api/tools/{tool_name}` API.
- Resolving only the first repeated API Key or Authorization Header. Proxies may preserve or combine duplicate values differently, so `/mcp` credential extraction must collect every value and reject conflicts instead of silently selecting one.
- Forgetting to proxy current runtime entrypoints from the web host. Production Nginx and the local Vite dev server must forward `/mcp` and `/api/tools/` to the backend.
- Letting unknown SQL tables execute because the declared resource scope is non-empty. SQL Guard extraction must resolve to known resource snapshots.
- Assuming tag visibility ignores policy. Tags are visible only through resources the identity can discover.
- Putting SQL safety checks in connectors. Connectors execute already-approved read-only SQL; SQL Guard and policy checks belong in runtime services.
- Treating the runtime engine cache as a global deployment-wide pool. It is per process, so multi-worker deployments multiply the effective maximum database connections.
- Representing connector failures as empty result sets or zero values. Runtime callers must branch on `status`; an `error` response is a failed query, not a successful query with no rows.
