# Acceptance Criteria: MCP API Key 多来源鉴权

**Spec:** `docs/superpowers/specs/2026-07-13-mcp-api-key-authentication-design.md`
**Date:** 2026-07-13
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | `/mcp` 接受默认 `X-ADG-API-Key` Header 中的有效 runtime API Key。 | API | 已创建绑定有效目录用户且具有 `runtime` scope 的 API Key。 | MCP 客户端以该 Header 初始化会话并调用 `list_datasources`，初始化成功且响应包含预置数据源。 |
| AC-002 | `/mcp` 使用 `ADG_API_KEY_HEADER` 设置的自定义 Header 名称。 | API | 将 `ADG_API_KEY_HEADER` 设为非默认值，并创建有效 runtime API Key。 | MCP 客户端使用该自定义 Header 初始化会话成功；默认 Header 不再作为该来源读取。 |
| AC-003 | `/mcp` 仅在显式启用兼容开关后接受固定查询参数 `apikey` 中的有效 runtime API Key。 | API | 已创建有效 runtime API Key，并设置 `ADG_MCP_QUERY_API_KEY_ENABLED=true`。 | 默认配置仅发送 query 时返回 HTTP 401；显式启用后访问 `/mcp?apikey=<key>` 的 MCP 客户端可初始化会话并调用 `list_datasources`。 |
| AC-004 | `/mcp` 接受 `Authorization: Bearer <key>` 中的有效 runtime API Key。 | API | 已创建有效 runtime API Key。 | 使用 `Authorization: bEaReR <key>` 的 MCP 客户端可初始化会话并调用 `list_datasources`。 |
| AC-005 | `/mcp` 对多个一致的非空来源只校验同一把 API Key。 | API | 已创建有效 runtime API Key；涉及 query 时已启用兼容开关。 | 同时发送 Header、`apikey` 和 Bearer，且三个值相同，请求可初始化 MCP 会话。 |
| AC-006 | `/mcp` 拒绝多个不同的非空 API Key 值。 | API | 请求同时携带至少两个已启用来源的不同 Header、`apikey` 或 Bearer 值。 | 请求在调用 API Key 数据库校验前返回 HTTP 400。 |
| AC-007 | `/mcp` 对没有启用来源中的可用凭证保持现有缺失凭证响应。 | API | 请求不含 API Key Header 或有效 Bearer；query 为空，或兼容开关未启用。 | 返回 HTTP 401，响应体的 `detail` 为 `Missing API key`。 |
| AC-008 | `/mcp` 保持现有无效、过期和缺少 runtime scope API Key 的鉴权结果。 | API | 分别创建无效值、已过期 Key 和缺少 `runtime` scope 的有效 Key。 | 无效或过期 Key 返回 HTTP 401；缺少 runtime scope 的 Key 返回 HTTP 403，且 `detail` 为 `Runtime scope required`。 |
| AC-009 | 新增的 query 与 Bearer 方式不扩展到补充 HTTP 工具接口。 | API | 已创建有效 runtime API Key。 | 对 `/api/tools/list_datasources` 仅发送 `apikey` 或 Bearer 时返回 HTTP 401 `Missing API key`；使用既有 Header 时仍可成功。 |
| AC-010 | 两个 README 都准确记录 MCP 的三种鉴权方式与 query 风险。 | Logic | 打开根目录英文 README 和中文 README。 | 两份 README 都列出 `/mcp` 的 Header、`apikey` 与 Bearer 用法，说明它们共用 runtime API Key，并建议优先使用 Header/Bearer 且提示 query 参数可能进入日志。 |
