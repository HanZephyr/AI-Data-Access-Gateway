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
  - docs/superpowers/memory/modules/milestone-2-datasource-foundation.md
last_verified_commit: f9b49a3
status: active
---

# Milestone 3 MCP Runtime

## Responsibilities

- Provide transport-neutral runtime tool handlers for datasource, tag, resource, preview, and query workflows.
- Expose `POST /mcp/tools/{tool_name}` as an authenticated MCP-style HTTP facade.
- Enforce runtime resource and field policies over Milestone 2 resource snapshots.
- Parse SQL through a conservative AST-based guard before read-only connector execution.
- Record runtime audit events for discovery, successful execution, SQL rejection, and permission rejection.

## Entry points

- Runtime service: `src/adg/gateway_runtime/tools.py`
- HTTP facade: `src/adg/mcp_api/tools.py`
- Policy service: `src/adg/policy/runtime.py`
- SQL Guard: `src/adg/sql_guard/guard.py`
- Governance models: `src/adg/control_plane/models/governance.py`
- Query connector contract: `src/adg/connectors/base.py`
- Relational query execution: `src/adg/connectors/relational.py`

## Invariants

- Runtime tool calls use `require_api_key`, not `require_admin_api_key`; admin scope is not required for MCP-style callers.
- Request payload identity context is trusted only after API key authentication.
- Runtime policy evaluation defaults to allow only when no active policies exist for the tenant/action.
- When active policies exist for a tenant/action, matching allow is required and matching deny wins.
- Field policies only narrow access after parent resource access has been granted.
- SQL Guard accepts only one `SELECT`/`WITH` style read-only statement and rejects mutation, DDL, transaction, multi-statement, and non-whitelisted function use.
- SQL resources extracted from SQL must map to known resource snapshots. Unknown or ambiguous SQL resources must be rejected before connector execution.
- Declared `resource_ids` are an intent scope; actual SQL resource extraction remains authoritative.

## Extension points

- A later stdio/SSE MCP protocol server should call `GatewayRuntimeService` rather than duplicate tool authorization logic.
- Milestone 4 masking should attach after policy checks and before rows are returned.
- Milestone 5 web console can manage the governance tables added here.
- Additional connector types can implement the shared `execute_query` contract without changing runtime tool dispatch.

## Common pitfalls

- Treating `POST /mcp/tools/{tool_name}` as full MCP protocol support. It is a deterministic HTTP facade for the runtime tools.
- Letting unknown SQL tables execute because the declared resource scope is non-empty. SQL Guard extraction must resolve to known resource snapshots.
- Assuming tag visibility is global. Tags are visible only through resources the identity can discover.
- Putting SQL safety checks in connectors. Connectors execute already-approved read-only SQL; SQL Guard and policy checks belong in runtime services.
