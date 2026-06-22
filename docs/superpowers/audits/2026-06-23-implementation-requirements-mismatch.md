# 实际实现与需求/文档不匹配审计：MCP 运行时入口

**日期：** 2026-06-23  
**范围：** 仅确认运行时 MCP/HTTP 工具入口与相关文档描述是否一致；本审计不包含功能代码修改。  
**结论级别：** 文档事实确认，不直接判定为代码缺陷。

## 要点

- 当前实现暴露两个入口：FastMCP Streamable HTTP 挂载在 `/mcp`，简化 HTTP 工具接口为 `POST /api/tools/{tool_name}`。
- 当前 release-facing 文档未发现仍描述 `POST /mcp/tools/{tool_name}` 的不一致；英文 README 与中文 README 已描述 `/mcp` 和 `/api/tools/{tool_name}`。
- 2026-04-24 的历史内部设计、验收和记忆文档仍保留 `POST /mcp/tools/{tool_name}` 以及调用方传入身份上下文的旧表述，已被当前实现和后续 2026-04-26 身份改造材料覆盖。
- 不应把旧内部文档里的路径直接判成代码缺陷。除非产品明确要求保留旧路径兼容，否则当前实现与当前对外文档是一致的。

## 当前实现证据

| 证据 | 事实 |
| --- | --- |
| `src/adg/app/main.py:16`、`:60` | 主应用导入并注册 `mcp_tools_router`。 |
| `src/adg/app/main.py:61` | 主应用将 FastMCP 应用挂载到 `/mcp`。 |
| `src/adg/mcp_api/tools.py:11`、`:14` | 简化 HTTP 工具路由是 `APIRouter(prefix="/api/tools")` + `@router.post("/{tool_name}")`，组合后为 `POST /api/tools/{tool_name}`。 |
| `src/adg/mcp_api/tools.py:19`、`:31` | 工具调用通过 `require_runtime_api_key` 鉴权，并使用 API Key 绑定的 `runtime_identity`，不是请求体中的调用方身份字段。 |
| `src/adg/mcp_server/server.py:18`、`:83-92` | FastMCP 服务通过 `runtime_mcp_server.streamable_http_app()` 构建 Streamable HTTP 应用。 |
| `tests/integration/test_mcp_tools_api.py:136`、`:245`、`:258` | 集成测试覆盖 `/api/tools/list_datasources`、`/api/tools/not_a_tool`，并拒绝请求体中的 `user_id`、`roles`、`groups`。 |
| `examples/mcp_client_http.py:13`、`:35` | 示例客户端调用 `/api/tools/{tool_name}`，并说明运行时身份来自绑定的 API Key。 |
| `web/nginx.conf:40-41` | 前端 nginx 代理显式转发 `/api/tools/` 到后端 `/api/tools/`。 |

## Release-Facing 文档一致性

本次检查的 release-facing 范围包括 `README.md`、`docs/zh-CN/README.md`、`docs/en`、`docs/zh-CN`。

| 文档 | 判断 | 证据 |
| --- | --- | --- |
| `README.md` | 未发现不一致 | `README.md:11` 描述 FastMCP Streamable HTTP `/mcp` 与简化 `/api/tools/{tool_name}` HTTP 工具接口。 |
| `docs/zh-CN/README.md` | 未发现不一致 | `docs/zh-CN/README.md:11` 与英文 README 同步，描述 `/mcp` 和 `/api/tools/{tool_name}`。 |
| `docs/en`、`docs/zh-CN` | 未发现旧路径命中 | 针对 `/mcp/tools`、`POST /mcp`、`/api/tools`、`FastMCP Streamable HTTP` 的扫描未发现 release-facing 文档仍把旧路径作为当前接口。 |

因此，当前 release-facing 文档已经纠正历史路径，不需要基于这些 README 再发起代码修复。

## 历史内部文档过期点

| 文档 | 过期描述 | 当前判断 |
| --- | --- | --- |
| `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md:24` | 将 HTTP facade 描述为 `POST /mcp/tools/{tool_name}`。 | 与当前 `/api/tools/{tool_name}` 实现不一致，应标记为历史表述或在后续整理时更新。 |
| `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md:66` | 常见误区仍围绕 `POST /mcp/tools/{tool_name}` 展开。 | 该误区本身仍有价值，但路径名称已过期。 |
| `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md:26` | 将 HTTP facade 定义为 `POST /mcp/tools/{tool_name}`，并要求请求体包含身份上下文。 | 被当前实现和 2026-04-26 身份改造覆盖。 |
| `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md:30` | 描述调用方通过请求体提供身份上下文。 | 当前运行时身份来自绑定的 API Key，旧身份模型已过期。 |
| `docs/superpowers/acceptance/2026-04-24-milestone-3-mcp-runtime.md:13-14` | 验收项使用 `POST /mcp/tools/list_datasources` 和 `POST /mcp/tools/not_a_tool`。 | 属于早期验收口径，不应覆盖当前代码事实。 |

后续内部材料已给出覆盖证据：

- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:19` 要求运行时端点拒绝请求体中的 `user_id`、`roles`、`groups`。
- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:40` 要求 MCP setup 指引不再展示调用方身份字段。
- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:41` 要求直接 HTTP 工具文档和路由使用 `/api/tools/{tool_name}`，并通过运行时 key 鉴权。

## 是否需要产品确认

当前实现是否“错误”不需要产品确认：从代码、测试、示例、nginx 代理和当前 README 看，`/mcp` 与 `/api/tools/{tool_name}` 是一致的当前事实。

仍建议产品或维护者确认以下契约问题：

1. 是否明确不支持 `POST /mcp/tools/{tool_name}` 作为兼容旧内部文档的别名。
2. 是否在对外材料中持续区分“FastMCP Streamable HTTP `/mcp`”与“简化 HTTP 工具接口 `/api/tools/{tool_name}`”，避免把后者称为完整 MCP 协议入口。
3. 历史内部文档是否保持原样作为批准时点记录，还是追加“已被当前实现和 2026-04-26 身份改造覆盖”的注记。

## 建议处理方式

- 保留当前功能代码，不因 2026-04-24 历史材料中的旧路径修改路由。
- 不回退 README 中已纠正的 `/mcp` 与 `/api/tools/{tool_name}` 表述。
- 后续如整理 `docs/superpowers` 历史材料，优先采用“加注 superseded/obsolete 说明”的方式，避免重写历史设计审批记录造成时间线混乱。
- 如果产品确认需要旧路径兼容，再另起功能任务评估 `POST /mcp/tools/{tool_name}` 别名、鉴权、测试与文档影响；该事项不属于本次审计文档任务。
