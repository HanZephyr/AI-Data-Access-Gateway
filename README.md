# AI Data Access Gateway

AI Data Access Gateway is a secure data access gateway for AI agents. It exposes controlled metadata discovery and read-only data access while enforcing authorization, SQL safety checks, masking, reversible desensitization, internal decryption, and audit logging.

## Development

Install backend development dependencies:

```bash
uv run --extra dev pytest
```

Seed demo data:

```bash
uv run --extra dev python examples/seed_demo.py --database-url sqlite:///./data/adg-control-plane.db
```

Run the backend:

```bash
$env:ADG_CONTROL_PLANE_DATABASE_URL="sqlite:///./data/adg-control-plane.db"
uv run --extra dev uvicorn adg.app.main:create_app --factory --reload
```

Run the web console:

```bash
cd web
npm install
npm run dev
```

Open the console:

```text
http://127.0.0.1:5173
API key: adg_admin
```

Run backend verification:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
```

Run frontend verification:

```bash
cd web
npm run build
```

Call MCP-style HTTP tools:

```bash
uv run --extra dev python examples/mcp_client_http.py --api-key adg_admin
```

Run with Docker Compose:

```bash
docker compose up --build
```

Milestone 1 includes the backend package skeleton, settings, FastAPI health endpoints, SQLite control-plane database setup, initial Alembic migration, API key validation, and audit event persistence.

Milestone 2 adds datasource CRUD, connector registry and thin relational adapters, metadata scanning, and resource snapshot persistence.

Milestone 3 adds MCP-style runtime tool handlers, an authenticated HTTP tool facade, conservative SQL Guard, runtime resource and field policy checks, tag visibility, read-only connector execution, and runtime audit events.

Milestone 4 adds masking policies, fixed/partial/hash/reversible masking, decrypt contexts, internal decrypt API support, and masking/decrypt audit events.

Milestone 5 adds admin APIs for console workflows and a Vite React + Ant Design web console under `web/`.

Milestone 6 adds demo seed data, a minimal HTTP MCP client example, Docker Compose packaging, V1 quickstart instructions, and final quality gates for the demo path.
