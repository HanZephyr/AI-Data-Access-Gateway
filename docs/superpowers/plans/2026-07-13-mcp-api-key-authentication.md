# MCP API Key 多来源鉴权实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 仅为 `/mcp` 增加 query 与 Bearer API Key 入口，同时保持既有 Header、运行时授权及普通 HTTP 工具接口行为不变。

**Architecture:** 在 `RuntimeApiKeyMiddleware` 内部使用一个纯提取函数收集配置 Header、查询参数和 Bearer 值。提取函数只负责规范化来源与识别冲突；现有 `authenticate_runtime_api_key_value` 继续负责数据库校验、scope、身份和限流。双语 README 只记录 `/mcp` 的三种入口及 query 风险。

**Tech Stack:** Python 3.12、FastAPI/Starlette、FastMCP、pytest、Markdown。

---

### Task 1: 测试驱动实现 `/mcp` 多来源凭证提取

**Files:**
- Modify: `tests/integration/test_mcp_streamable_http.py`
- Modify: `tests/integration/test_mcp_tools_api.py`
- Modify: `src/adg/mcp_server/server.py:33-82`

- [ ] **Step 1: 写入失败的 Streamable HTTP MCP 鉴权测试**

在 `tests/integration/test_mcp_streamable_http.py` 中提取现有初始化/`list_datasources` 调用为辅助函数，并增加以下参数化测试；Header、query、Bearer 三组请求必须实际完成 MCP 初始化和工具调用：

```python
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("headers", "query"),
    [
        ({"X-ADG-API-Key": "adg_runtime"}, ""),
        ({}, "?apikey=adg_runtime"),
        ({"Authorization": "bEaReR adg_runtime"}, ""),
    ],
)
async def test_streamable_mcp_server_accepts_runtime_api_key_sources(
    headers: dict[str, str],
    query: str,
) -> None:
    app, _ = build_streamable_mcp_app()
    await assert_mcp_list_datasources(app, headers=headers, query=query)
```

再增加：自定义 `ADG_API_KEY_HEADER` 的成功路径、三个来源相同的成功路径、不同非空来源返回 HTTP 400，以及未提供凭证返回 HTTP 401 `Missing API key`。在 `tests/integration/test_mcp_tools_api.py` 增加 query 与 Bearer 调用 `POST /api/tools/list_datasources` 时仍返回 HTTP 401 的断言。

- [ ] **Step 2: 运行新增测试并确认失败原因是缺少新来源支持**

Run: `uv run --extra dev pytest tests/integration/test_mcp_streamable_http.py tests/integration/test_mcp_tools_api.py -q`

Expected: query 与 Bearer 的 `/mcp` 成功测试失败并返回现有的 `Missing API key`；冲突凭证测试尚未得到 HTTP 400。

- [ ] **Step 3: 在 MCP 中间件中实现最小凭证提取器**

在 `src/adg/mcp_server/server.py` 中使用 `QueryParams`，并在调用现有 `_authenticate` 前解析 API Key：

```python
def _extract_bearer_api_key(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        return None
    return parts[1].strip() or None


def _extract_api_key_from_scope(scope: Scope) -> str | None:
    headers = Headers(raw=scope["headers"])
    candidates = [
        headers.get(get_settings().api_key_header),
        *QueryParams(scope["query_string"]).getlist("apikey"),
        _extract_bearer_api_key(headers.get("authorization")),
    ]
    supplied_keys = {candidate for candidate in candidates if candidate}
    if len(supplied_keys) > 1:
        raise HTTPException(status_code=400, detail="Conflicting API key credentials")
    return next(iter(supplied_keys), None)
```

将中间件的 `try` 块改为先调用 `_extract_api_key_from_scope(scope)`，再把结果传给原有 `self._authenticate`。不要修改 `authenticate_runtime_api_key_value`、普通 FastAPI 依赖或路由挂载。

- [ ] **Step 4: 运行新增测试并确认全部通过**

Run: `uv run --extra dev pytest tests/integration/test_mcp_streamable_http.py tests/integration/test_mcp_tools_api.py -q`

Expected: exit code 0；所有目标测试通过。

- [ ] **Step 5: 提交运行时代码与回归测试**

```powershell
git add src/adg/mcp_server/server.py tests/integration/test_mcp_streamable_http.py tests/integration/test_mcp_tools_api.py
git commit -m "feat(mcp): support query and bearer api keys"
```

### Task 2: 同步双语 MCP 鉴权文档

**Files:**
- Modify: `README.md:49`
- Modify: `docs/zh-CN/README.md:49`

- [ ] **Step 1: 在两份 README 的 runtime API Key 说明后新增 MCP 鉴权小节**

英文 README 使用以下等价内容，中文 README 使用完整中文翻译：

```markdown
### MCP authentication

`/mcp` accepts one runtime-scoped API key through any one of these forms:

- `X-ADG-API-Key: <runtime-api-key>`
- `Authorization: Bearer <runtime-api-key>`
- `http://<host>/mcp?apikey=<runtime-api-key>`

All forms authenticate the same runtime API key. Prefer the Header or Bearer form. Use the query parameter only when the Agent platform cannot set request headers, and ensure proxies, access logs, and monitoring do not retain full query strings.
```

说明多个不同非空来源会被拒绝，并且该段仅描述 `/mcp`，不得暗示 `/api/tools/{tool_name}` 支持 query 或 Bearer。

- [ ] **Step 2: 检查双语内容与实现范围**

Run: `git diff --check; rg -n "MCP authentication|MCP 鉴权|apikey|Authorization: Bearer" README.md docs/zh-CN/README.md`

Expected: exit code 0；两份 README 都包含 Header、Bearer、`apikey`、同一 runtime API Key 与 query 日志风险说明。

- [ ] **Step 3: 提交文档更新**

```powershell
git add README.md docs/zh-CN/README.md
git commit -m "docs(mcp): document api key authentication options"
```

### Task 3: 全量验证与验收映射

**Files:**
- Verify: `tests/integration/test_mcp_streamable_http.py`
- Verify: `tests/integration/test_mcp_tools_api.py`
- Verify: `src/adg/mcp_server/server.py`
- Verify: `README.md`
- Verify: `docs/zh-CN/README.md`

- [ ] **Step 1: 执行后端质量门禁**

Run: `uv run --extra dev pytest; uv run --extra dev ruff check .; uv run --extra dev mypy src tests`

Expected: 三个命令均以 exit code 0 结束。

- [ ] **Step 2: 依据验收标准逐项核对**

核对 `docs/superpowers/acceptance/2026-07-13-mcp-api-key-authentication.md` 中 AC-001 至 AC-010：测试输出覆盖 AC-001 至 AC-009，README 静态检查覆盖 AC-010。仅在每一项都有可复核证据时报告完成。
