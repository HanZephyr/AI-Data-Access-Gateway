# 实际实现与需求/文档不匹配审计：MCP 运行时入口

**日期：** 2026-06-23
**范围：** 确认运行时 FastMCP/普通 HTTP 工具入口与相关文档描述是否一致；本审计不包含功能代码修改。
**结论级别：** 产品确认后的文档事实记录，不直接判定为代码缺陷。

## 要点

- 当前实现暴露两个入口：面向 AI Agent 的主入口是 FastMCP Streamable HTTP `/mcp`，面向传统服务集成的补充普通 HTTP 工具接口是 `POST /api/tools/{tool_name}`。
- 产品已确认不支持 `POST /mcp/tools/{tool_name}` 作为兼容旧内部文档的别名。
- 对外材料需要持续区分 FastMCP 接口与普通 HTTP 接口，避免把 `POST /api/tools/{tool_name}` 描述成 MCP 传输入口或主入口。
- 2026-04-24 的历史内部设计、验收和早期记忆文档中关于 `POST /mcp/tools/{tool_name}` 以及调用方传入身份上下文的旧表述，已被当前实现和 2026-04-26 身份改造覆盖。

## 当前实现证据

| 证据 | 事实 |
| --- | --- |
| `src/adg/app/main.py:16`、`:60` | 主应用导入并注册 `mcp_tools_router`。 |
| `src/adg/app/main.py:61` | 主应用将 FastMCP 应用挂载到 `/mcp`。 |
| `src/adg/mcp_api/tools.py:11`、`:14` | 补充普通 HTTP 工具路由是 `APIRouter(prefix="/api/tools")` + `@router.post("/{tool_name}")`，组合后为 `POST /api/tools/{tool_name}`。 |
| `src/adg/mcp_api/tools.py:19`、`:31` | 工具调用通过 `require_runtime_api_key` 鉴权，并使用 API Key 绑定的 `runtime_identity`，不是请求体中的调用方身份字段。 |
| `src/adg/mcp_server/server.py:18`、`:83-92` | FastMCP 服务通过 `runtime_mcp_server.streamable_http_app()` 构建 Streamable HTTP 应用。 |
| `tests/integration/test_mcp_tools_api.py:136`、`:245`、`:258` | 集成测试覆盖 `/api/tools/list_datasources`、`/api/tools/not_a_tool`，并拒绝请求体中的 `user_id`、`roles`、`groups`。 |
| `examples/mcp_client_http.py:13`、`:35` | 示例客户端调用 `/api/tools/{tool_name}`，并说明运行时身份来自绑定的 API Key。 |
| `web/nginx.conf:40-41` | 前端 nginx 代理显式转发 `/api/tools/` 到后端 `/api/tools/`。 |

## Release-Facing 文档一致性

本次检查的 release-facing 范围包括 `README.md`、`docs/zh-CN/README.md`、`docs/en`、`docs/zh-CN`。

| 文档 | 判断 | 证据 |
| --- | --- | --- |
| `README.md` | 未发现不一致 | `README.md:11` 区分面向 AI Agent 的 FastMCP Streamable HTTP `/mcp` 主入口与面向传统服务集成的补充普通 HTTP 工具接口 `POST /api/tools/{tool_name}`。 |
| `docs/zh-CN/README.md` | 未发现不一致 | `docs/zh-CN/README.md:11` 与英文 README 同步，区分 `/mcp` 主入口和 `POST /api/tools/{tool_name}` 补充普通 HTTP 工具接口。 |
| `docs/en`、`docs/zh-CN` | 未发现旧路径命中 | 针对 `/mcp/tools`、`POST /mcp`、`/api/tools`、`FastMCP Streamable HTTP` 的扫描未发现 release-facing 文档仍把旧路径作为当前接口。 |

因此，当前 release-facing 文档已经纠正历史路径，并应继续保持 FastMCP 主入口与补充普通 HTTP 入口的边界。

## 历史内部文档过期点

| 文档 | 过期描述 | 当前处理状态 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md:26` | 将 HTTP facade 定义为 `POST /mcp/tools/{tool_name}`，并要求请求体包含身份上下文。 | 已追加注记：该路径和身份模型已被当前实现和 2026-04-26 身份改造覆盖，且不支持旧路径兼容别名。 |
| `docs/superpowers/specs/2026-04-24-milestone-3-mcp-runtime-design.md:30` | 描述调用方通过请求体提供身份上下文。 | 已追加同一覆盖注记；当前运行时身份来自绑定的 API Key。 |
| `docs/superpowers/acceptance/2026-04-24-milestone-3-mcp-runtime.md:13-14` | 验收项使用 `POST /mcp/tools/list_datasources` 和 `POST /mcp/tools/not_a_tool`。 | 已追加注记：旧验收路径已被当前实现和 2026-04-26 身份改造覆盖，且不支持旧路径兼容别名。 |
| `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md` | 早期记忆曾保留 `POST /mcp/tools/{tool_name}` 表述。 | 已更新为当前契约：`/mcp` 是 AI Agent 主入口，`POST /api/tools/{tool_name}` 是传统服务补充普通 HTTP 入口。 |

后续内部材料已给出覆盖证据：

- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:19` 要求运行时端点拒绝请求体中的 `user_id`、`roles`、`groups`。
- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:40` 要求 MCP setup 指引不再展示调用方身份字段。
- `docs/superpowers/acceptance/2026-04-26-user-directory-runtime-identity-redesign.md:41` 要求直接 HTTP 工具文档和路由使用 `/api/tools/{tool_name}`，并通过运行时 key 鉴权。

## 产品确认结论

当前实现是否“错误”不需要再确认：从代码、测试、示例、nginx 代理和当前 README 看，`/mcp` 与 `POST /api/tools/{tool_name}` 是一致的当前事实。2026-06-23 产品确认进一步明确：

1. `POST /api/tools/{tool_name}` 只作为 MCP 服务的补充调用方式，主要服务非 AI Agent 的传统服务集成；它不是主入口。
2. 明确不支持 `POST /mcp/tools/{tool_name}` 作为兼容旧内部文档的别名。
3. 对外材料需要持续区分“FastMCP Streamable HTTP `/mcp`”与“补充普通 HTTP 工具接口 `POST /api/tools/{tool_name}`”，避免把后者称为 MCP 传输入口。
4. 历史内部文档需要追加“已被当前实现和 2026-04-26 身份改造覆盖”的注记。

## 建议处理方式

- 保留当前功能代码，不因 2026-04-24 历史材料中的旧路径修改路由。
- 保持 README 与管理台文案持续区分 `/mcp` 主入口和 `POST /api/tools/{tool_name}` 补充普通 HTTP 入口。
- 后续整理 `docs/superpowers` 历史材料时采用“加注 superseded/obsolete 说明”的方式，避免重写历史设计审批记录造成时间线混乱。
- 不实现 `POST /mcp/tools/{tool_name}` 兼容别名；若后续再次提出该需求，需要先重新评估安全边界、鉴权、测试与文档影响。
