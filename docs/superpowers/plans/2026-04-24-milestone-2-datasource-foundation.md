# Milestone 2 Datasource Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add datasource CRUD, connector registry and thin adapters, metadata scanning, and resource snapshot persistence on top of the Milestone 1 backend.

**Architecture:** Extend the existing FastAPI service with datasource models plus migrations, a connector contract and registry, a snapshot persistence service, and authenticated admin routes for CRUD, connection testing, and scanning. Metadata scanning stays relational and uses normalized snapshot shapes so Milestone 3 can consume stable control-plane data.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, pytest, HTTPX, Ruff, Mypy.

---

## File Structure

- Create: `src/adg/connectors/__init__.py`
- Create: `src/adg/connectors/base.py`
- Create: `src/adg/connectors/errors.py`
- Create: `src/adg/connectors/registry.py`
- Create: `src/adg/connectors/relational.py`
- Create: `src/adg/connectors/postgres/__init__.py`
- Create: `src/adg/connectors/postgres/adapter.py`
- Create: `src/adg/connectors/mysql/__init__.py`
- Create: `src/adg/connectors/mysql/adapter.py`
- Create: `src/adg/connectors/doris/__init__.py`
- Create: `src/adg/connectors/doris/adapter.py`
- Create: `src/adg/control_plane/models/datasource.py`
- Create: `src/adg/control_plane/models/resource.py`
- Create: `src/adg/control_plane/services/__init__.py`
- Create: `src/adg/control_plane/services/datasource_service.py`
- Create: `src/adg/control_plane/services/metadata_scan_service.py`
- Create: `src/adg/admin_api/datasources.py`
- Modify: `src/adg/control_plane/models/__init__.py`
- Modify: `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`
- Modify: `src/adg/app/main.py`
- Modify: `tests/integration/test_migrations.py`
- Create: `tests/unit/connectors/test_registry.py`
- Create: `tests/unit/control_plane/test_datasource_service.py`
- Create: `tests/integration/test_admin_datasources.py`
- Create: `tests/integration/test_metadata_scan.py`

## Task 1: Datasource And Snapshot Models

**Files:**
- Create: `src/adg/control_plane/models/datasource.py`
- Create: `src/adg/control_plane/models/resource.py`
- Modify: `src/adg/control_plane/models/__init__.py`
- Test: `tests/unit/control_plane/test_datasource_service.py`

- [ ] **Step 1: Write the failing model registration tests**

```python
from adg.control_plane.models import Base
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField


def test_datasource_and_snapshot_models_are_registered() -> None:
    assert Datasource.__tablename__ == "datasources"
    assert Resource.__tablename__ == "resources"
    assert ResourceField.__tablename__ == "resource_fields"
    assert "datasources" in Base.metadata.tables
    assert "resources" in Base.metadata.tables
    assert "resource_fields" in Base.metadata.tables
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/control_plane/test_datasource_service.py -v`
Expected: FAIL with `ModuleNotFoundError` for new model modules.

- [ ] **Step 3: Write minimal datasource and snapshot models**

Implement `Datasource`, `Resource`, and `ResourceField` with UUID string ids, timestamp columns, foreign keys by string id, and JSON payloads stored as text.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/control_plane/test_datasource_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/models tests/unit/control_plane/test_datasource_service.py
git commit -m "feat: add datasource snapshot models"
```

## Task 2: Connector Contract And Registry

**Files:**
- Create: `src/adg/connectors/__init__.py`
- Create: `src/adg/connectors/base.py`
- Create: `src/adg/connectors/errors.py`
- Create: `src/adg/connectors/registry.py`
- Create: `src/adg/connectors/relational.py`
- Create: `src/adg/connectors/postgres/__init__.py`
- Create: `src/adg/connectors/postgres/adapter.py`
- Create: `src/adg/connectors/mysql/__init__.py`
- Create: `src/adg/connectors/mysql/adapter.py`
- Create: `src/adg/connectors/doris/__init__.py`
- Create: `src/adg/connectors/doris/adapter.py`
- Test: `tests/unit/connectors/test_registry.py`

- [ ] **Step 1: Write the failing registry tests**

Include tests for:

- supported connector lookup for `postgres`, `mysql`, `doris`
- unsupported connector lookup error
- missing driver error message helper

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/connectors/test_registry.py -v`
Expected: FAIL because connector modules do not exist.

- [ ] **Step 3: Implement the connector protocol, errors, registry, and thin adapters**

Use a shared relational helper for SQLAlchemy URL building and inspection. Adapters only need `test_connection()` and `scan_metadata()` for Milestone 2.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/connectors/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/connectors tests/unit/connectors/test_registry.py
git commit -m "feat: add connector registry and relational adapters"
```

## Task 3: Datasource Services And Migrations

**Files:**
- Create: `src/adg/control_plane/services/__init__.py`
- Create: `src/adg/control_plane/services/datasource_service.py`
- Create: `src/adg/control_plane/services/metadata_scan_service.py`
- Modify: `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`
- Modify: `tests/integration/test_migrations.py`
- Test: `tests/unit/control_plane/test_datasource_service.py`

- [ ] **Step 1: Write the failing service and migration tests**

Add tests that verify:

- datasource create, update, delete, and list behavior
- metadata scan persistence replaces prior snapshot rows
- Alembic creates `datasources`, `resources`, and `resource_fields`

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/control_plane/test_datasource_service.py tests/integration/test_migrations.py -v`
Expected: FAIL because service modules and new tables are missing.

- [ ] **Step 3: Implement services and migration updates**

Write minimal CRUD and snapshot replacement logic. Keep scan persistence transactional.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/control_plane/test_datasource_service.py tests/integration/test_migrations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/services src/adg/control_plane/migrations tests/unit/control_plane/test_datasource_service.py tests/integration/test_migrations.py
git commit -m "feat: add datasource services and snapshot migrations"
```

## Task 4: Admin Datasource APIs

**Files:**
- Create: `src/adg/admin_api/datasources.py`
- Modify: `src/adg/app/main.py`
- Test: `tests/integration/test_admin_datasources.py`

- [ ] **Step 1: Write the failing admin API tests**

Cover:

- create/list/get/update/delete datasource routes
- 404 for missing datasource
- admin auth requirement

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_admin_datasources.py -v`
Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement datasource admin router**

Mount the router under `/admin/datasources` and wire it to the datasource service.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_admin_datasources.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api/datasources.py src/adg/app/main.py tests/integration/test_admin_datasources.py
git commit -m "feat: add admin datasource crud api"
```

## Task 5: Test And Scan Endpoints

**Files:**
- Modify: `src/adg/admin_api/datasources.py`
- Create: `tests/integration/test_metadata_scan.py`

- [ ] **Step 1: Write the failing scan and test endpoint tests**

Cover:

- successful connection test
- successful scan with deterministic resource and field counts
- replacement of old snapshots on repeat scan

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_metadata_scan.py -v`
Expected: FAIL because test and scan endpoints are missing.

- [ ] **Step 3: Implement admin test and scan endpoints**

Use connector registry plus metadata scan service. Tests may override the registry with a fake connector.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_metadata_scan.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api/datasources.py tests/integration/test_metadata_scan.py
git commit -m "feat: add datasource test and scan endpoints"
```

## Task 6: Full Verification

**Files:**
- Modify: `README.md` if new Milestone 2 commands or notes are needed

- [ ] **Step 1: Update README if needed**

Document datasource admin and scan capability only if a new operator command or caveat is needed.

- [ ] **Step 2: Run full verification**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src tests
```

Expected:

- pytest: all tests pass
- ruff: no lint errors
- mypy: no type errors

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: note milestone 2 datasource foundation"
```
