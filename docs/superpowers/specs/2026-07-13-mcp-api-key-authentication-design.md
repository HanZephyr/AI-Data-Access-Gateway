# MCP API Key 多来源鉴权设计

## 目标

为 FastMCP Streamable HTTP 入口 `/mcp` 增加两种 API Key 传递方式，以兼容无法自定义请求头的 Agent 平台，同时保持现有运行时 API Key 的鉴权、授权和身份绑定逻辑不变。

## 范围

- 保留现有由 `ADG_API_KEY_HEADER` 配置的请求头方式，默认 Header 为 `X-ADG-API-Key`。
- 新增由 `ADG_MCP_QUERY_API_KEY_ENABLED` 显式开启的固定查询参数 `apikey`，例如 `/mcp?apikey=<key>`；默认关闭。
- 新增 `Authorization: Bearer <key>`；`Bearer` 前缀大小写不敏感，并在校验前去除前缀与分隔空白。
- 仅作用于 `/mcp`。补充 HTTP 工具接口 `POST /api/tools/{tool_name}`、管理接口与内部接口保持现有 Header 鉴权行为。

## 非目标

- 不引入新的 API Key 类型、scope 或身份模型。
- 不改变 API Key 哈希校验、过期检查、runtime scope 检查、身份加载和鉴权失败限流。
- 不为 query 参数新增可配置名称。

## 鉴权流程

`RuntimeApiKeyMiddleware` 在调用既有运行时鉴权函数前，收集以下候选凭证：

1. `ADG_API_KEY_HEADER` 指定的 Header。
2. 启用兼容开关时的查询参数 `apikey`。
3. 符合 `Bearer <key>` 格式的 `Authorization` Header。

只有一个非空候选值，或多个非空候选值完全相同，便将该值传给既有运行时鉴权逻辑。多个非空候选值不同则在访问数据库前返回 HTTP 400，防止不一致配置被静默掩盖。

没有可用候选值时继续返回 HTTP 401 `Missing API key`。开关关闭时 query 参数不参与候选值或冲突判断。无效、过期或不具备 runtime scope 的 API Key 沿用现有状态码与响应。

## 测试

- 验证默认/已配置 Header 和 Bearer 均可完成 MCP 初始化及工具调用，query 默认关闭且显式开启后可用。
- 验证 `bearer` 前缀不区分大小写。
- 验证不同来源携带不同值时返回 HTTP 400。
- 验证 `/api/tools/{tool_name}` 不接受新增的 query 或 Bearer 来源。

## 文档

同步更新英文 `README.md` 和中文 `docs/zh-CN/README.md`：说明三种 `/mcp` 鉴权方式共用同一把 runtime API Key，并明确建议优先使用 Header 或 Bearer。查询参数仅用于无法设置 Header 的平台，部署方需要确保代理、访问日志和监控不会记录完整查询字符串。
