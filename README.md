# AI Data Access Gateway

AI Data Access Gateway is a secure data access gateway for AI agents. It exposes controlled metadata discovery and read-only data access while enforcing authorization, SQL safety checks, masking, reversible desensitization, runtime decryption, and audit logging.

## Development

Install backend development dependencies:

```bash
uv run --extra dev pytest
```

Seed demo data:

```bash
uv run --extra dev python examples/seed_demo.py --database-url sqlite:///./data/adg-control-plane.db
```

The command prints a one-time random admin API key in JSON. Keep that value and use it in the console and CLI examples below.

Run the backend:

```bash
$env:ADG_CONTROL_PLANE_DATABASE_URL="sqlite:///./data/adg-control-plane.db"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY="<generate-a-second-long-random-secret>"
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
API key: <the admin_api_key printed by seed_demo.py>
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
uv run --extra dev python examples/mcp_client_http.py --api-key <the admin_api_key printed by seed_demo.py>
```

Production bootstrap flow:

```bash
uv run --extra dev alembic upgrade head
uv run --extra dev init-admin --database-url sqlite:///./data/adg-control-plane.db
```

`init-admin` prints a one-time random admin API key for the control plane. Store it immediately, then use it to create scoped replacement keys from the console.

Run with Docker Compose:

```bash
$env:ADG_SECRET_KEY = "<generate-a-long-random-secret>"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY = "<generate-a-second-long-random-secret>"
docker compose up --build
docker exec -it ai-data-access-gateway-backend-1 init-admin
```

The production-style Compose stack starts:

- backend API on `http://127.0.0.1:8000`
- web console on `http://127.0.0.1:8080`

The web container serves the built Vite bundle through Nginx and proxies `/admin`, `/mcp`, `/internal`, and `/health` requests to the backend service. It no longer runs `npm run dev` or bind-mounts the repository.

Milestone 1 includes the backend package skeleton, settings, FastAPI health endpoints, SQLite control-plane database setup, initial Alembic migration, API key validation, and audit event persistence.

Milestone 2 adds datasource CRUD, connector registry and thin relational adapters, metadata scanning, and resource snapshot persistence.

Milestone 3 adds MCP-style runtime tool handlers, an authenticated HTTP tool facade, conservative SQL Guard, runtime resource and field policy checks, tag visibility, read-only connector execution, and runtime audit events.

Milestone 4 adds masking policies, fixed/partial/hash/reversible masking, decrypt contexts, runtime decrypt API support, and masking/decrypt audit events.

Milestone 5 adds admin APIs for console workflows and a Vite React + Ant Design web console under `web/`.

Milestone 6 adds demo seed data, a minimal HTTP MCP client example, Docker Compose packaging, V1 quickstart instructions, and final quality gates for the demo path.
