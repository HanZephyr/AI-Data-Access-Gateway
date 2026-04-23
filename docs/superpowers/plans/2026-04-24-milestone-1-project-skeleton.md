# Milestone 1 Project Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable backend foundation for AI Data Access Gateway: package skeleton, FastAPI app, settings, control-plane database, migrations, API key validation, and audit foundation.

**Architecture:** Implement a single FastAPI service under `src/adg` with clear internal module boundaries from the approved V1 design. Use SQLAlchemy models and Alembic migrations for the SQLite control-plane database. Keep Milestone 1 intentionally narrow so later plans can add connectors, MCP tools, policies, masking, and the web console without restructuring.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2.x, Alembic, SQLite, pytest, HTTPX, Ruff, Mypy.

---

## Scope Check

The approved V1 spec covers multiple independent subsystems: runtime query flow, connectors, MCP tools, SQL Guard, masking, decrypt API, audit, and web console. This plan implements only Milestone 1: project skeleton and control-plane foundation. Later plans should cover Milestones 2-6 separately.

## File Structure

Create these files:

- `pyproject.toml`: package metadata, runtime dependencies, optional database connector extras, test/lint tooling.
- `.env.example`: documented local development settings.
- `README.md`: initial quickstart for installing, testing, and running the backend.
- `src/adg/__init__.py`: package version.
- `src/adg/app/__init__.py`: app package marker.
- `src/adg/app/settings.py`: Pydantic settings loaded from environment.
- `src/adg/app/main.py`: FastAPI application factory and health endpoints.
- `src/adg/app/dependencies.py`: shared FastAPI dependencies, including API key auth.
- `src/adg/control_plane/__init__.py`: control-plane package marker.
- `src/adg/control_plane/db.py`: SQLAlchemy engine, session factory, session dependency.
- `src/adg/control_plane/models/__init__.py`: model exports for Alembic.
- `src/adg/control_plane/models/base.py`: SQLAlchemy declarative base.
- `src/adg/control_plane/models/api_key.py`: `ApiKey` ORM model.
- `src/adg/audit/__init__.py`: audit package marker.
- `src/adg/audit/models.py`: `AuditEvent` ORM model.
- `src/adg/audit/service.py`: audit event writer.
- `src/adg/shared/__init__.py`: shared package marker.
- `src/adg/shared/security.py`: API key generation, hashing, and verification.
- `src/adg/shared/errors.py`: shared exception types.
- `alembic.ini`: Alembic config.
- `src/adg/control_plane/migrations/env.py`: Alembic migration environment.
- `src/adg/control_plane/migrations/script.py.mako`: Alembic revision template.
- `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`: initial migration.
- `tests/conftest.py`: pytest fixtures.
- `tests/unit/app/test_settings.py`: settings tests.
- `tests/integration/test_health.py`: app health tests.
- `tests/unit/shared/test_security.py`: API key security tests.
- `tests/integration/test_api_key_auth.py`: API key dependency tests.
- `tests/integration/test_audit_service.py`: audit write tests.

## Task 1: Package Metadata And Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/adg/__init__.py`
- Create: `src/adg/app/__init__.py`

- [ ] **Step 1: Write package/tooling files**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.24"]
build-backend = "hatchling.build"

[project]
name = "ai-data-access-gateway"
version = "0.1.0"
description = "Secure data access gateway for AI agents."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
authors = [{ name = "AI Data Access Gateway Contributors" }]
dependencies = [
  "alembic>=1.13.2",
  "fastapi>=0.115.0",
  "pydantic-settings>=2.4.0",
  "sqlalchemy>=2.0.32",
  "uvicorn[standard]>=0.30.6",
]

[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.2.1"]
mysql = ["pymysql>=1.1.1"]
doris = ["pymysql>=1.1.1"]
all = ["psycopg[binary]>=3.2.1", "pymysql>=1.1.1"]
dev = [
  "httpx>=0.27.2",
  "mypy>=1.11.2",
  "pytest>=8.3.2",
  "pytest-cov>=5.0.0",
  "ruff>=0.6.4",
]

[project.scripts]
adg-api = "adg.app.main:run"

[tool.hatch.build.targets.wheel]
packages = ["src/adg"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_configs = true
plugins = []
```

Create `.env.example`:

```dotenv
ADG_ENV=local
ADG_SERVICE_NAME=AI Data Access Gateway
ADG_CONTROL_PLANE_DATABASE_URL=sqlite:///./data/adg-control-plane.db
ADG_API_KEY_HEADER=X-ADG-API-Key
ADG_SECRET_KEY=change-me-to-a-long-random-secret
ADG_DEFAULT_TENANT_ID=default
ADG_LOG_LEVEL=INFO
```

Create `README.md`:

```markdown
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
```

Create `src/adg/__init__.py`:

```python
"""AI Data Access Gateway package."""

__version__ = "0.1.0"
```

Create `src/adg/app/__init__.py`:

```python
"""FastAPI application package."""
```

- [ ] **Step 2: Run metadata checks**

Run:

```bash
python -m pip install -e ".[dev]"
python -m pytest --collect-only
```

Expected:

```text
no tests collected
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml .env.example README.md src/adg/__init__.py src/adg/app/__init__.py
git commit -m "chore: add python project skeleton"
```

## Task 2: Settings

**Files:**
- Create: `src/adg/app/settings.py`
- Test: `tests/unit/app/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/app/test_settings.py`:

```python
from adg.app.settings import Settings


def test_settings_defaults_are_local_friendly() -> None:
    settings = Settings()

    assert settings.env == "local"
    assert settings.service_name == "AI Data Access Gateway"
    assert settings.api_key_header == "X-ADG-API-Key"
    assert settings.default_tenant_id == "default"
    assert settings.control_plane_database_url.startswith("sqlite:///")


def test_settings_read_adg_prefixed_environment(monkeypatch) -> None:
    monkeypatch.setenv("ADG_ENV", "test")
    monkeypatch.setenv("ADG_CONTROL_PLANE_DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("ADG_SECRET_KEY", "unit-test-secret")

    settings = Settings()

    assert settings.env == "test"
    assert settings.control_plane_database_url == "sqlite:///./test.db"
    assert settings.secret_key == "unit-test-secret"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/app/test_settings.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'adg.app.settings'`.

- [ ] **Step 3: Implement settings**

Create `src/adg/app/settings.py`:

```python
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "test", "production"] = "local"
    service_name: str = "AI Data Access Gateway"
    control_plane_database_url: str = "sqlite:///./data/adg-control-plane.db"
    api_key_header: str = "X-ADG-API-Key"
    secret_key: str = Field(default="change-me-to-a-long-random-secret", min_length=16)
    default_tenant_id: str = "default"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/app/test_settings.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/app/settings.py tests/unit/app/test_settings.py
git commit -m "feat: add application settings"
```

## Task 3: FastAPI Application Factory And Health Checks

**Files:**
- Create: `src/adg/app/main.py`
- Test: `tests/integration/test_health.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_health.py`:

```python
from fastapi.testclient import TestClient

from adg.app.main import create_app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Data Access Gateway",
    }


def test_ready_endpoint_returns_ready_status() -> None:
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'adg.app.main'`.

- [ ] **Step 3: Implement the app factory**

Create `src/adg/app/main.py`:

```python
import uvicorn
from fastapi import FastAPI

from adg.app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.service_name)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["system"])
    def ready() -> dict[str, str]:
        return {"status": "ready"}

    return app


def run() -> None:
    uvicorn.run("adg.app.main:create_app", factory=True, host="127.0.0.1", port=8000)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_health.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/app/main.py tests/integration/test_health.py
git commit -m "feat: add fastapi health endpoints"
```

## Task 4: Control-Plane Database Session

**Files:**
- Create: `src/adg/control_plane/__init__.py`
- Create: `src/adg/control_plane/models/__init__.py`
- Create: `src/adg/control_plane/models/base.py`
- Create: `src/adg/control_plane/db.py`
- Create: `tests/conftest.py`
- Test: `tests/unit/control_plane/test_db.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/control_plane/test_db.py`:

```python
from sqlalchemy import text

from adg.control_plane.db import create_engine_from_url, create_session_factory


def test_create_session_factory_executes_sql() -> None:
    engine = create_engine_from_url("sqlite:///:memory:")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("select 1")).scalar_one()

    assert result == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/control_plane/test_db.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'adg.control_plane'`.

- [ ] **Step 3: Implement database foundation**

Create `src/adg/control_plane/__init__.py`:

```python
"""Control-plane persistence and governance configuration."""
```

Create `src/adg/control_plane/models/__init__.py`:

```python
from adg.control_plane.models.base import Base

__all__ = ["Base"]
```

Create `src/adg/control_plane/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `src/adg/control_plane/db.py`:

```python
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from adg.app.settings import get_settings


def create_engine_from_url(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    poolclass: type[StaticPool] | None = None
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url == "sqlite:///:memory:":
            poolclass = StaticPool
    return create_engine(
        database_url,
        connect_args=connect_args,
        future=True,
        poolclass=poolclass,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


engine = create_engine_from_url(get_settings().control_plane_database_url)
SessionLocal = create_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
```

Create `tests/conftest.py`:

```python
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models import Base


@pytest.fixture
def sqlite_engine() -> Engine:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(sqlite_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(sqlite_engine)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Session:
    with session_factory() as session:
        yield session
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/control_plane/test_db.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane tests/conftest.py tests/unit/control_plane/test_db.py
git commit -m "feat: add control plane database session"
```

## Task 5: API Key Model And Security Helpers

**Files:**
- Create: `src/adg/control_plane/models/api_key.py`
- Create: `src/adg/shared/__init__.py`
- Create: `src/adg/shared/security.py`
- Test: `tests/unit/shared/test_security.py`
- Test: `tests/unit/control_plane/test_api_key_model.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/shared/test_security.py`:

```python
from adg.shared.security import generate_api_key, hash_api_key, verify_api_key


def test_generate_api_key_uses_adg_prefix() -> None:
    raw_key = generate_api_key()

    assert raw_key.startswith("adg_")
    assert len(raw_key) > 32


def test_hash_and_verify_api_key() -> None:
    raw_key = "adg_test_secret"
    hashed = hash_api_key(raw_key)

    assert hashed != raw_key
    assert verify_api_key(raw_key, hashed)
    assert not verify_api_key("adg_wrong_secret", hashed)
```

Create `tests/unit/control_plane/test_api_key_model.py`:

```python
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey


def test_api_key_model_is_registered() -> None:
    assert "api_keys" in Base.metadata.tables
    assert ApiKey.__tablename__ == "api_keys"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/shared/test_security.py tests/unit/control_plane/test_api_key_model.py -v
```

Expected: FAIL because `adg.shared.security` and `ApiKey` do not exist.

- [ ] **Step 3: Implement API key model and helpers**

Create `src/adg/shared/__init__.py`:

```python
"""Shared helpers and value objects."""
```

Create `src/adg/shared/security.py`:

```python
import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    return f"adg_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    candidate = hash_api_key(raw_key)
    return hmac.compare_digest(candidate, hashed_key)
```

Create `src/adg/control_plane/models/api_key.py`:

```python
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adg.control_plane.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
```

Update `src/adg/control_plane/models/__init__.py`:

```python
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.base import Base

__all__ = ["ApiKey", "Base"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/unit/shared/test_security.py tests/unit/control_plane/test_api_key_model.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/shared src/adg/control_plane/models tests/unit/shared tests/unit/control_plane/test_api_key_model.py
git commit -m "feat: add api key model and hashing"
```

## Task 6: Audit Model And Service

**Files:**
- Create: `src/adg/audit/__init__.py`
- Create: `src/adg/audit/models.py`
- Create: `src/adg/audit/service.py`
- Test: `tests/integration/test_audit_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_audit_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent
from adg.audit.service import AuditService


def test_audit_service_records_event(db_session: Session) -> None:
    service = AuditService(db_session)

    event = service.record_event(
        tenant_id="default",
        user_id="u_123",
        api_key_id="key_123",
        event_type="metadata",
        decision="allow",
        datasource_id="ds_123",
        resource_ids=["res_1"],
        query_id=None,
        sql_text=None,
        reason=None,
        metadata={"tool": "list_datasources"},
    )
    db_session.commit()

    stored = db_session.execute(select(AuditEvent)).scalar_one()
    assert stored.id == event.id
    assert stored.tenant_id == "default"
    assert stored.event_type == "metadata"
    assert stored.resource_ids_json == '["res_1"]'
    assert stored.metadata_json == '{"tool":"list_datasources"}'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_audit_service.py -v
```

Expected: FAIL because `adg.audit` does not exist.

- [ ] **Step 3: Implement audit model and service**

Create `src/adg/audit/__init__.py`:

```python
"""Audit event persistence."""
```

Create `src/adg/audit/models.py`:

```python
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adg.control_plane.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    datasource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    resource_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    query_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    sql_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
```

Create `src/adg/audit/service.py`:

```python
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent


class AuditService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_event(
        self,
        *,
        tenant_id: str,
        user_id: Optional[str],
        api_key_id: Optional[str],
        event_type: str,
        decision: str,
        datasource_id: Optional[str],
        resource_ids: list[str],
        query_id: Optional[str],
        sql_text: Optional[str],
        reason: Optional[str],
        metadata: dict[str, Any],
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            api_key_id=api_key_id,
            event_type=event_type,
            datasource_id=datasource_id,
            resource_ids_json=json.dumps(resource_ids, separators=(",", ":")),
            query_id=query_id,
            sql_text=sql_text,
            decision=decision,
            reason=reason,
            metadata_json=json.dumps(metadata, separators=(",", ":")),
        )
        self._session.add(event)
        return event
```

Update `src/adg/control_plane/models/__init__.py`:

```python
from adg.audit.models import AuditEvent
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.base import Base

__all__ = ["ApiKey", "AuditEvent", "Base"]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_audit_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/audit src/adg/control_plane/models/__init__.py tests/integration/test_audit_service.py
git commit -m "feat: add audit event foundation"
```

## Task 7: Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `src/adg/control_plane/migrations/env.py`
- Create: `src/adg/control_plane/migrations/script.py.mako`
- Create: `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`
- Test: `tests/integration/test_migrations.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_migrations.py`:

```python
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_creates_foundation_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "control-plane.db"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    assert {"api_keys", "audit_events", "alembic_version"}.issubset(tables)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_migrations.py -v
```

Expected: FAIL because `alembic.ini` does not exist.

- [ ] **Step 3: Add Alembic config and initial migration**

Create `alembic.ini`:

```ini
[alembic]
script_location = src/adg/control_plane/migrations
prepend_sys_path = .
sqlalchemy.url = sqlite:///./data/adg-control-plane.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `src/adg/control_plane/migrations/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from adg.app.settings import get_settings
from adg.control_plane.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return get_settings().control_plane_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `src/adg/control_plane/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`:

```python
"""initial control plane

Revision ID: 202604240001
Revises:
Create Date: 2026-04-24

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202604240001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.String(length=200), nullable=True),
        sa.Column("api_key_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("datasource_id", sa.String(length=36), nullable=True),
        sa.Column("resource_ids_json", sa.Text(), nullable=False),
        sa.Column("query_id", sa.String(length=36), nullable=True),
        sa.Column("sql_text", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_api_key_id", "audit_events", ["api_key_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_datasource_id", "audit_events", ["datasource_id"])
    op.create_index("ix_audit_events_query_id", "audit_events", ["query_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_query_id", table_name="audit_events")
    op.drop_index("ix_audit_events_datasource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_api_key_id", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_migrations.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alembic.ini src/adg/control_plane/migrations tests/integration/test_migrations.py
git commit -m "feat: add initial control plane migration"
```

## Task 8: API Key Authentication Dependency

**Files:**
- Create: `src/adg/shared/errors.py`
- Create: `src/adg/app/dependencies.py`
- Test: `tests/integration/test_api_key_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_api_key_auth.py`:

```python
from collections.abc import Iterator

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.shared.security import hash_api_key


def build_test_app(raw_key: str) -> FastAPI:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_123",
                name="test",
                key_hash=hash_api_key(raw_key),
                status="active",
                scopes='["mcp","internal","admin"]',
            )
        )
        session.commit()

    app = FastAPI()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    @app.get("/protected")
    def protected(api_key: AuthenticatedApiKey = Depends(require_api_key)) -> dict[str, str]:
        return {"api_key_id": api_key.id}

    return app


def test_require_api_key_accepts_valid_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected", headers={"X-ADG-API-Key": "adg_valid"})

    assert response.status_code == 200
    assert response.json() == {"api_key_id": "key_123"}


def test_require_api_key_rejects_missing_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_require_api_key_rejects_wrong_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_api_key_auth.py -v
```

Expected: FAIL because `adg.app.dependencies` does not exist.

- [ ] **Step 3: Implement authentication dependency**

Create `src/adg/shared/errors.py`:

```python
class AdgError(Exception):
    """Base class for domain errors."""
```

Create `src/adg/app/dependencies.py`:

```python
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.db import get_session
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import verify_api_key


@dataclass(frozen=True)
class AuthenticatedApiKey:
    id: str
    scopes: str


def require_api_key(
    raw_api_key: str | None = Header(default=None, alias="X-ADG-API-Key"),
    session: Session = Depends(get_session),
) -> AuthenticatedApiKey:
    if raw_api_key is None or raw_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_keys = session.execute(
        select(ApiKey).where(ApiKey.status == "active")
    ).scalars()

    for api_key in api_keys:
        if verify_api_key(raw_api_key, api_key.key_hash):
            return AuthenticatedApiKey(id=api_key.id, scopes=api_key.scopes)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_api_key_auth.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/shared/errors.py src/adg/app/dependencies.py tests/integration/test_api_key_auth.py
git commit -m "feat: add api key authentication dependency"
```

## Task 9: Protected Admin Foundation Route

**Files:**
- Create: `src/adg/admin_api/__init__.py`
- Create: `src/adg/admin_api/system.py`
- Modify: `src/adg/app/main.py`
- Test: `tests/integration/test_admin_system.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_admin_system.py`:

```python
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.control_plane.db import get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.shared.security import hash_api_key


def test_admin_system_endpoint_requires_api_key() -> None:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_admin",
                name="admin",
                key_hash=hash_api_key("adg_admin"),
                status="active",
                scopes='["admin"]',
            )
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)

    missing = client.get("/admin/system")
    assert missing.status_code == 401

    ok = client.get("/admin/system", headers={"X-ADG-API-Key": "adg_admin"})
    assert ok.status_code == 200
    assert ok.json() == {
        "service": "AI Data Access Gateway",
        "api_key_id": "key_admin",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_admin_system.py -v
```

Expected: FAIL because `/admin/system` returns 404.

- [ ] **Step 3: Implement protected admin route**

Create `src/adg/admin_api/__init__.py`:

```python
"""Admin REST API routers."""
```

Create `src/adg/admin_api/system.py`:

```python
from fastapi import APIRouter, Depends

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.app.settings import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system")
def system(api_key: AuthenticatedApiKey = Depends(require_api_key)) -> dict[str, str]:
    return {
        "service": get_settings().service_name,
        "api_key_id": api_key.id,
    }
```

Update `src/adg/app/main.py`:

```python
import uvicorn
from fastapi import FastAPI

from adg.admin_api.system import router as admin_system_router
from adg.app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.service_name)
    app.include_router(admin_system_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["system"])
    def ready() -> dict[str, str]:
        return {"status": "ready"}

    return app


def run() -> None:
    uvicorn.run("adg.app.main:create_app", factory=True, host="127.0.0.1", port=8000)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_admin_system.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api src/adg/app/main.py tests/integration/test_admin_system.py
git commit -m "feat: add protected admin system route"
```

## Task 10: Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with Milestone 1 commands**

Replace `README.md` with:

```markdown
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
```

- [ ] **Step 2: Run full verification**

Run:

```bash
pytest
ruff check .
mypy src tests
```

Expected:

```text
pytest: all tests pass
ruff: no lint errors
mypy: no type errors
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add milestone 1 development commands"
```

## Self-Review Checklist

- Spec coverage: This plan covers Milestone 1 from the approved design: FastAPI app, settings, database foundation, migrations, API key validation, and audit foundation.
- Deferred spec areas: connectors, metadata scanning, MCP tools, policies, SQL Guard, masking, decrypt API, web console, demos, and Docker are intentionally left for later milestone plans.
- Red-flag scan: The plan avoids deferred work language; every implementation step includes concrete files, code, commands, and expected results.
- Type consistency: `ApiKey`, `AuditEvent`, `Base`, `Settings`, `create_app`, `get_session`, `require_api_key`, and `AuditService` names are introduced before later tasks use them.
