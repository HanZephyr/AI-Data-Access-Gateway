# Milestone 3 MCP Runtime Design

**Date:** 2026-04-24
**Status:** Approved

> 注记（2026-06-23）：本文档中的 `POST /mcp/tools/{tool_name}` 路径和“请求体提供身份上下文”身份模型已被当前实现和 2026-04-26 身份改造覆盖。当前 AI Agent 主入口是 FastMCP Streamable HTTP `/mcp`；`POST /api/tools/{tool_name}` 仅作为面向传统服务集成的补充普通 HTTP 工具接口；不支持 `POST /mcp/tools/{tool_name}` 作为兼容别名。

---

## Scope

Milestone 3 implements the backend runtime surface used by MCP-style callers. It exposes stable tool handlers for datasource discovery, tag/resource discovery, resource description, previews, and read-only SQL execution. The milestone also adds the minimum control-plane policy and tag tables required for runtime authorization checks.

This milestone remains backend-only. It does not implement masking or reversible decrypt behavior, web-console pages, Docker packaging, or full MCP transport negotiation. The HTTP route added here is a deterministic tool-call facade that later MCP protocol wiring can reuse.

## Runtime Surface

The runtime exposes these tools through a shared service and an authenticated HTTP facade:

- `list_datasources`
- `list_tags`
- `list_resources`
- `list_resources_by_tag`
- `describe_resource`
- `preview_resource`
- `execute_query`

The HTTP facade is `POST /mcp/tools/{tool_name}`. Requests must include a valid API key and an identity context in the JSON body. The service layer stays transport-neutral so a later stdio/SSE MCP server can call the same handlers without duplicating authorization logic.

## Identity Context

Runtime calls use API key authentication plus request-supplied identity context:

```json
{
  "user_id": "user-1",
  "roles": ["analyst"],
  "groups": ["finance"]
}
```

The authenticated API key proves the caller is trusted to provide this context. Runtime tools do not require the admin scope.

## Tags and Policies

Milestone 3 adds control-plane models and baseline migration entries for:

- `tags`
- `resource_tags`
- `resource_policies`
- `field_policies`

Policy checks are conservative and deterministic:

- inactive policies are ignored
- matching deny policies override matching allow policies
- if at least one active policy exists for an action, access requires a matching allow
- if no active policies exist for an action, access is allowed
- field policies can only narrow access after the parent resource is allowed

Supported policy subjects are `user`, `role`, `group`, and `all`. Resource policies may match a specific resource or tag. Field policies match a resource plus field name.

## SQL Guard

SQL Guard parses SQL with `sqlglot` and accepts only one read-only statement. It allows `SELECT` and `WITH`, rejects mutation/DDL/transaction statements, rejects non-whitelisted functions, records referenced tables and columns, and injects a limit when the caller omits one.

V1 uses a conservative profile with a small function allowlist:

- `count`
- `sum`
- `avg`
- `min`
- `max`

The guard returns a structured result with `allowed`, `normalized_sql`, `statement_type`, `accessed_resources`, `accessed_fields`, `used_functions`, `risk_level`, `rejection_reasons`, and `warnings`.

## Query Execution

Connectors gain a relational read-only query method that accepts a normalized SQL string and row limit. The runtime checks declared `resource_ids` first, then compares SQL Guard extracted resources to known resource snapshots for the datasource. Actual resource access must be covered by declared scope and resource policy checks.

`preview_resource` generates a simple `SELECT * FROM <resource_path> LIMIT n` for relational table/view resources and runs it through the same connector execution path. Milestone 4 will add masking to the response pipeline.

## Audit

Runtime tools record audit events for metadata discovery, query execution, SQL rejection, and permission rejection. Events include user, API key id, datasource id when available, resource ids, query id when available, SQL text when applicable, decision, reason, and lightweight metadata.

## Testing

Tests cover:

- SQL Guard allow/reject behavior and limit injection
- policy decision precedence and default behavior
- resource and tag discovery visibility
- describe/preview/execute tool behavior through the service
- authenticated HTTP facade behavior
- migration table creation
