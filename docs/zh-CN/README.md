# AI Data Access Gateway

[English README](../../README.md)

AI Data Access Gateway 是一个面向 AI Agent 的开源安全数据访问网关。它位于 AI Agent 与真实数据源之间，提供受治理的元数据发现与只读运行时访问，并在执行过程中落实鉴权、SQL 安全检查、字段级策略、脱敏、运行时解密控制与审计日志。

## 项目状态

当前仓库以 V1 MVP 形式发布，适合本地评估、引导式演示和持续迭代的开源协作。它不应被描述为已经达到企业级控制平面、零信任平台或生产级全面加固状态。

## 当前已实现

- 基于 FastAPI 的后端服务，提供管理、运行时、FastMCP Streamable HTTP `/mcp` 接口，以及更简单的 `/api/tools/{tool_name}` HTTP 工具接口
- 基于 API Key 的管理访问与运行时访问
- 与目录用户、角色绑定的密钥派生运行时身份
- 面向关系型数据源的数据源注册、元数据扫描与资源快照持久化
- 资源级与字段级访问策略校验
- 只读取向的保守 SQL Guard
- 固定值、局部、哈希、可逆脱敏，以及运行时解密控制
- 审计事件持久化与原始 SQL 访问收敛
- React + Vite 管理控制台
- 演示种子数据、Docker Compose 打包与 HTTP MCP 风格客户端示例

## MVP 边界

- 没有独立的管理员登录系统、SSO 或 MFA
- 没有行级策略执行
- 没有面向多管理员协作的后台 RBAC 模型
- 仓库内不自带 TLS 终止或完整生产部署加固
- 当前不应宣称具备企业级生产落地能力

## 架构概览

项目由控制平面、运行时访问层和管理控制台组成。控制平面负责数据源登记、目录身份映射、资源元数据、字段策略、脱敏配置与 API Key 管理；运行时访问层通过 SQL Guard、资源策略和字段策略限制查询，只允许受控的只读路径，并同时暴露 FastMCP Streamable HTTP `/mcp` 端点与更简单的 `/api/tools/{tool_name}` HTTP 工具接口；管理控制台为单管理员信任模型服务，覆盖数据源维护、资源治理与审计查看等操作。仓库还包含演示数据初始化、Docker Compose 启动方式，以及最小化的运行时 HTTP 调用示例。

## 仓库布局

- `src/adg/`：后端应用、控制平面、运行时、连接器与安全能力
- `tests/`：后端单元与集成测试
- `web/`：React + Vite 管理控制台
- `examples/`：演示种子数据和示例客户端流程
- `docs/superpowers/`：内部规划、设计、验收与仓库记忆文档

## 快速开始

### 后端

```powershell
uv sync --extra dev --extra all
uv run --extra dev python examples/seed_demo.py --database-url sqlite:///./data/adg-control-plane.db
$env:ADG_CONTROL_PLANE_DATABASE_URL="sqlite:///./data/adg-control-plane.db"
$env:ADG_SECRET_KEY="<generate-a-long-random-secret>"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY="<generate-a-second-long-random-secret>"
uv run --extra dev uvicorn adg.app.main:create_app --factory --reload
```

`seed_demo.py` 会输出一次性的管理员 API Key，用于控制台初始化和管理面配置。请立即保存，并在控制台中使用该值。运行时 HTTP 示例需要另一个绑定目录用户的 runtime 作用域 API Key，该 Key 需要在初始化完成后单独创建或重置。

### 前端

```powershell
Set-Location web
npm ci
npm run dev
```

默认开发地址为 `http://127.0.0.1:5173`。

### Docker Compose

```powershell
$env:ADG_SECRET_KEY="<generate-a-long-random-secret>"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY="<generate-a-second-long-random-secret>"
docker compose up --build
docker compose exec backend init-admin
```

Compose 方案会启动生产风格的后端与静态前端容器，其中 Web 控制台默认暴露在 `http://127.0.0.1:8080`。

## 验证命令

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
uv export --frozen --extra dev --extra all --no-editable --no-hashes --no-emit-project --format requirements-txt --output-file .tmp-audit-requirements.txt
uv tool run --from pip-audit pip-audit -r .tmp-audit-requirements.txt
Remove-Item .tmp-audit-requirements.txt
```

## 文档导航

- [项目现状](status.md)
- [路线图](roadmap.md)
- [安全策略镜像](security.md)
- [贡献指南镜像](contributing.md)
- [行为准则镜像](code-of-conduct.md)
- [English README](../../README.md)
- [English Status](../en/status.md)
- [English Roadmap](../en/roadmap.md)
- [English Security Policy](../../SECURITY.md)
- [English Contributing](../../CONTRIBUTING.md)
- [English Code Of Conduct](../../CODE_OF_CONDUCT.md)

## 许可证

项目采用 Apache 2.0 许可证。详情见 [LICENSE](../../LICENSE)。
