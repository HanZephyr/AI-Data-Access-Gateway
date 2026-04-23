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

Run the backend:

```bash
uvicorn adg.app.main:create_app --factory --reload
```

Open:

```text
http://127.0.0.1:8000/health
```
