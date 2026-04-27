# AI Data Access Gateway

[Chinese Mirror / 中文镜像](docs/zh-CN/README.md) | [Chinese Status / 中文项目现状](docs/zh-CN/status.md) | [Chinese Roadmap / 中文路线图](docs/zh-CN/roadmap.md)

AI Data Access Gateway is an open-source secure data access gateway for AI agents. It sits between agentic systems and real datasources, exposing governed metadata discovery and read-only runtime access with authorization, conservative SQL validation, masking, runtime decrypt controls, and audit logging.

## Project Status

This repository is currently published as a V1 MVP. It is suitable for local evaluation, guided demos, and iterative open-source development. It should not be described as an enterprise-ready control plane or a production-hardened zero-trust platform in its current form.

## What It Does Today

- FastAPI backend with admin, runtime, internal decrypt, FastMCP Streamable HTTP at `/mcp`, and a simpler HTTP tool API at `/api/tools/{tool_name}`
- API-key-based admin, runtime, and internal access scopes
- Directory-backed runtime identity with users, roles, org nodes, and runtime key reset flows
- Relational datasource registration, metadata scanning, and resource snapshot persistence
- Resource and field policy enforcement for read-only runtime access
- Conservative SQL Guard validation that rejects unsafe or unsupported query patterns
- Fixed, partial, hash, and reversible masking with runtime decrypt support
- Audit event persistence for admin and runtime actions
- React + Vite admin console for onboarding, datasources, policies, masking, users, roles, imports, and audit review
- Demo seed data, example HTTP client flow, and Docker Compose packaging

## MVP Boundaries

- no separate admin login system, SSO, or MFA
- no row-level policy enforcement or SQL rewriting
- no multi-operator admin RBAC model
- no built-in TLS termination, secret manager integration, or high-availability deployment model

## Architecture

The repository ships as a single FastAPI service backed by SQLAlchemy models and Alembic migrations. The control plane stores datasources, resources, policies, masking rules, audit events, and directory entities. Runtime access is derived from authenticated API keys bound to users and roles, then narrowed through datasource, resource, field, and masking checks before rows are returned. The runtime surface is exposed both as FastMCP Streamable HTTP at `/mcp` and as a simpler HTTP tool route at `/api/tools/{tool_name}`. The admin console is a React + Vite application in development and a built static site behind Nginx in the Docker Compose path.

## Repository Layout

- `src/adg/`: backend application code, runtime services, admin APIs, and connector logic
- `tests/`: backend unit and integration coverage
- `web/`: React + Vite admin console
- `examples/`: demo seed data and HTTP client examples
- `docs/en/`: English release-facing documentation
- `docs/zh-CN/`: Chinese mirror documentation
- `docs/superpowers/`: internal planning, specs, and repository memory

## Quickstart

### Backend

```powershell
uv sync --extra dev --extra all
uv run --extra dev python examples/seed_demo.py --database-url sqlite:///./data/adg-control-plane.db
$env:ADG_CONTROL_PLANE_DATABASE_URL="sqlite:///./data/adg-control-plane.db"
$env:ADG_SECRET_KEY="<generate-a-long-random-secret>"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY="<generate-a-second-long-random-secret>"
uv run --extra dev uvicorn adg.app.main:create_app --factory --reload
```

The seed command prints a one-time admin API key for onboarding and admin setup. Open the console at `http://127.0.0.1:5173` and paste that key into the onboarding screen. The runtime HTTP example requires a separate runtime-scoped API key bound to a directory user, created or reset after setup.

### Frontend

```powershell
Set-Location web
npm ci
npm run dev
```

### Docker Compose

```powershell
$env:ADG_SECRET_KEY="<generate-a-long-random-secret>"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY="<generate-a-second-long-random-secret>"
docker compose up --build
docker compose exec backend init-admin
```

The Compose stack publishes the web console on `http://127.0.0.1:8080`.

## Verification

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

## Documentation

- [Project Status](docs/en/status.md)
- [Roadmap](docs/en/roadmap.md)
- [Chinese README](docs/zh-CN/README.md)
- [Chinese Status](docs/zh-CN/status.md)
- [Chinese Roadmap](docs/zh-CN/roadmap.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

Licensed under Apache 2.0. See [LICENSE](LICENSE).
