# 贡献指南

[English original](../../CONTRIBUTING.md)

## 范围

AI Data Access Gateway 当前以 V1 MVP 形式发布。贡献应优先选择范围清晰、易于评审的改动，而不是大面积、带有推测性的重构。凡是会实质影响对外发布行为或文档表述的变更，都应明确说明当前实现边界。

## 前置条件

- Python 3.12+
- Node.js 20+
- `uv`
- `npm`

## 本地环境准备

### 后端

```powershell
uv sync --extra dev --extra all
```

### 前端

```powershell
Set-Location web
npm ci
Set-Location ..
```

## 验证

在提交 Pull Request 之前，请先运行与你改动范围相对应的验证命令。

### 后端

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
```

### 前端

```powershell
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
```

## Pull Request 期望

- 保持改动聚焦，避免无关清理混入
- 行为变化时同步补齐或更新测试
- 面向发布的英文与中文文档变更应保持同步
- 不要声称仓库尚未实现的能力
- 保留工作树中与本次任务无关的用户或队友改动
- 如果改动影响安全、Schema 或 API 表面，请在 Pull Request 描述中明确说明

## 开发说明

- 以当前代码、测试与可运行配置作为事实来源。
- 历史设计文档可以提供上下文，但不能覆盖已经实现的行为。
- 如果确实需要做较大的改动，尽量拆分为顺序明确的多个 Pull Request，以便评审和回滚。
