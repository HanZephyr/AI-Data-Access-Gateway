# AI Data Access Gateway

AI Data Access Gateway is a secure data access gateway for AI agents. It exposes controlled metadata discovery and read-only data access while enforcing authorization, SQL safety checks, masking, reversible desensitization, internal decryption, and audit logging.

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

Run type checks:

```bash
mypy src tests
```

Run database migrations:

```bash
alembic upgrade head
```

Run the backend:

```bash
uvicorn adg.app.main:create_app --factory --reload
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

Milestone 1 includes the backend package skeleton, settings, FastAPI health endpoints, SQLite control-plane database setup, initial Alembic migration, API key validation, and audit event persistence.
