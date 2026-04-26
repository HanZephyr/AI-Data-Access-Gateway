# Runtime and Admin Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the runtime field-authorization gap, remove persistent browser storage of the admin key, encrypt persisted datasource secrets, remove policy priority, and reduce default raw-SQL exposure while preserving troubleshooting access.

**Architecture:** Tighten runtime validation in `SqlGuard` and `GatewayRuntimeService`, introduce a shared persisted-secret crypto helper used by datasource persistence and runtime connector execution, simplify governance models by removing `priority`, and split audit summary views from raw-SQL detail access. Update the React admin console to keep credentials in memory only and to edit datasource secrets with non-revealing placeholders.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, cryptography Fernet, React, Vite, Vitest, pytest, ruff, mypy.

---

## Tasks

### Task 1: Reject wildcard queries in SQL guard

**AC IDs:** AC-001, AC-002

**Files:**
- Modify: `tests/unit/sql_guard/test_guard.py`
- Modify: `src/adg/sql_guard/guard.py`

- [ ] **Step 1: Write failing SQL-guard tests for `*` and `table.*`.**

```python
def test_guard_rejects_select_star() -> None:
    result = SqlGuard().check("select * from public.customers")

    assert result.allowed is False
    assert result.normalized_sql is None
    assert "wildcard_projection_not_allowed" in result.rejection_reasons


def test_guard_rejects_qualified_wildcard() -> None:
    result = SqlGuard().check("select c.*, c.id from public.customers c")

    assert result.allowed is False
    assert result.normalized_sql is None
    assert "wildcard_projection_not_allowed" in result.rejection_reasons
```

- [ ] **Step 2: Run the SQL-guard tests and verify they fail for the right reason.**

Run: `uv run --extra dev pytest tests/unit/sql_guard/test_guard.py -v`

Expected: failures because wildcard projections are still accepted.

- [ ] **Step 3: Implement wildcard detection in `SqlGuard`.**

```python
def _has_wildcard_projection(self, statement: exp.Select) -> bool:
    return any(
        isinstance(projection, exp.Star)
        or (
            isinstance(projection, exp.Column)
            and isinstance(projection.this, exp.Star)
        )
        for projection in statement.expressions
    )
```

If `_has_wildcard_projection(statement)` is true, return a rejected `SqlGuardResult` with rejection reason `wildcard_projection_not_allowed`.

- [ ] **Step 4: Re-run the SQL-guard tests and verify they pass.**

Run: `uv run --extra dev pytest tests/unit/sql_guard/test_guard.py -v`

Expected: all tests in that file pass.

- [ ] **Step 5: Commit the SQL-guard change set.**

```bash
git add tests/unit/sql_guard/test_guard.py src/adg/sql_guard/guard.py
git commit -m "fix: reject wildcard runtime sql projections"
```

### Task 2: Enforce field-level authorization during execution and preview

**AC IDs:** AC-003, AC-004, AC-005, AC-006

**Files:**
- Modify: `tests/unit/gateway_runtime/test_tools.py`
- Modify: `src/adg/gateway_runtime/tools.py`
- Reuse: `src/adg/policy/runtime.py`

- [ ] **Step 1: Add failing runtime tests for denied fields, disabled fields, explicit preview columns, and zero-readable-field preview rejection.**

```python
def test_execute_query_rejects_denied_field_and_skips_connector(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add(
        FieldPolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
            status="active",
        )
    )

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id, email from public.customers",
        limit=10,
    )

    assert response["status"] == "rejected"
    assert response["reason"] == "field_access_denied:email"
```

Also add:
- one test that marks `email` disabled and expects rejection
- one test that checks `FakeConnector.last_sql == "SELECT id FROM ... LIMIT 1"` style explicit preview SQL
- one test that denies every active field and expects preview rejection without connector execution

- [ ] **Step 2: Run the runtime tests and verify they fail before implementation.**

Run: `uv run --extra dev pytest tests/unit/gateway_runtime/test_tools.py -v`

Expected: the new tests fail because execution still skips field checks and preview still uses `select *`.

- [ ] **Step 3: Implement execution-time field authorization and explicit preview query construction.**

```python
def _first_inaccessible_field(
    self,
    *,
    identity: IdentityContext,
    resources: list[Resource],
    accessed_fields: list[str],
) -> str | None:
    for resource in resources:
        for field_name in accessed_fields:
            decision = self._policy.check_field_access(
                identity=identity,
                resource=resource,
                field_name=field_name,
                action="read",
            )
            if not decision.allowed:
                return field_name
    return None
```

Then:
- call `_first_inaccessible_field(...)` from `execute_query()`
- reject with a stable reason like `field_access_denied:<field_name>`
- add `_preview_select_columns(...)` helper that loads readable active fields and returns a comma-joined explicit select list
- reject preview when the returned list is empty

- [ ] **Step 4: Re-run the runtime tests and verify they pass.**

Run: `uv run --extra dev pytest tests/unit/gateway_runtime/test_tools.py -v`

Expected: all runtime unit tests pass.

- [ ] **Step 5: Commit the runtime authorization change set.**

```bash
git add tests/unit/gateway_runtime/test_tools.py src/adg/gateway_runtime/tools.py
git commit -m "fix: enforce runtime field authorization"
```

### Task 3: Encrypt persisted datasource secrets and preserve update semantics

**AC IDs:** AC-007, AC-008, AC-009, AC-010, AC-011, AC-016

**Files:**
- Create: `src/adg/shared/secret_config.py`
- Create: `tests/unit/shared/test_secret_config.py`
- Modify: `src/adg/app/settings.py`
- Modify: `src/adg/control_plane/models/datasource.py`
- Modify: `src/adg/control_plane/services/datasource_service.py`
- Modify: `src/adg/connectors/relational.py`
- Modify: `src/adg/admin_api/datasources.py`
- Modify: `tests/unit/app/test_settings.py`
- Modify: `tests/unit/control_plane/test_datasource_service.py`
- Modify: `tests/integration/test_admin_datasources.py`

- [ ] **Step 1: Add failing tests for settings validation, secret envelope storage, omitted/blank update semantics, and decrypted connector runtime config.**

```python
def test_datasource_service_encrypts_password_before_persisting(db_session: Session) -> None:
    datasource = DatasourceService(db_session).create_datasource(
        name="Warehouse",
        connector_type="postgres",
        config={"host": "db", "database": "app", "username": "alice", "password": "secret"},
        status="active",
    )

    stored = json.loads(datasource.config_json)
    assert stored["password"] != "secret"
    assert stored["password"]["kind"] == "encrypted_secret"
```

Also add:
- one settings test that production rejects missing `ADG_CREDENTIAL_ENCRYPTION_KEY`
- one service test that omitted/blank password keeps the previous encrypted envelope unchanged
- one connector/runtime-oriented test that `config()` or equivalent decrypted runtime path yields plaintext password for connector use
- one integration test that datasource API responses never include plaintext password

- [ ] **Step 2: Run the datasource/settings tests and verify they fail.**

Run:
- `uv run --extra dev pytest tests/unit/app/test_settings.py -v`
- `uv run --extra dev pytest tests/unit/control_plane/test_datasource_service.py -v`
- `uv run --extra dev pytest tests/integration/test_admin_datasources.py -v`

Expected: failures because encrypted envelopes and keep-existing-secret semantics do not exist yet.

- [ ] **Step 3: Implement shared persisted-secret helpers and wire them through datasource persistence and connector use.**

```python
class SecretConfigService:
    def protect_persisted_config(self, config: dict[str, object], *, previous: dict[str, object] | None = None) -> dict[str, object]:
        ...

    def reveal_runtime_config(self, config: dict[str, object]) -> dict[str, object]:
        ...

    def redact_admin_config(self, config: dict[str, object]) -> dict[str, object]:
        ...
```

Implement these rules:
- encrypt non-empty password replacements
- preserve previous secret when field is missing or blank
- return placeholder objects, not plaintext, from admin serializers
- decrypt secrets only for runtime connector/test connection use

Add a dedicated `credential_encryption_key` setting with production validation.

- [ ] **Step 4: Re-run the datasource/settings tests and verify they pass.**

Run the same commands from Step 2.

Expected: all targeted settings, datasource service, and datasource API tests pass.

- [ ] **Step 5: Commit the datasource-secret hardening change set.**

```bash
git add src/adg/shared/secret_config.py tests/unit/shared/test_secret_config.py src/adg/app/settings.py src/adg/control_plane/models/datasource.py src/adg/control_plane/services/datasource_service.py src/adg/connectors/relational.py src/adg/admin_api/datasources.py tests/unit/app/test_settings.py tests/unit/control_plane/test_datasource_service.py tests/integration/test_admin_datasources.py
git commit -m "fix: encrypt persisted datasource secrets"
```

### Task 4: Update the admin UI for in-memory auth and secret placeholders

**AC IDs:** AC-008, AC-010, AC-012

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/src/configForms.ts`
- Modify: `web/src/PoliciesPage.test.tsx`
- Modify: `web/src/RolesPage.test.tsx`
- Modify: `web/src/UsersPage.test.tsx`
- Modify: `web/src/configForms.test.ts`
- Modify: `web/index.html`
- Modify: `web/nginx.conf`

- [ ] **Step 1: Add failing frontend tests that prove the admin key is not persisted and datasource secret placeholders normalize to “no change” unless replaced.**

```tsx
it("does not write the admin key to localStorage", async () => {
  localStorage.clear();
  render(<App />);
  await signInWithValidAdminKey();
  expect(localStorage.getItem("adg.apiKey")).toBeNull();
});
```

Also add a `configForms` test that an empty password edit result omits the password key from the update payload.

- [ ] **Step 2: Run the frontend tests and verify they fail.**

Run:
- `npm test -- main`
- `npm test -- configForms`

Expected: failures because `localStorage` is still used and secret edit normalization still echoes password values.

- [ ] **Step 3: Implement in-memory auth state, secret-placeholder editing, and baseline security headers.**

```tsx
const [apiKey, setApiKey] = useState("");

const saveApiKey = (value: string) => {
  setApiKey(value);
  setAuthError(null);
};
```

Also:
- remove all `adg.apiKey` storage reads/writes
- make datasource secret inputs render placeholder bullets without binding the stored value
- normalize blank secret edits to “omit field”
- add CSP and related headers in `web/nginx.conf`

- [ ] **Step 4: Re-run the frontend tests and verify they pass.**

Run:
- `npm test`

Expected: all frontend tests pass, including the new auth and config normalization assertions.

- [ ] **Step 5: Commit the admin UI hardening change set.**

```bash
git add web/src/main.tsx web/src/configForms.ts web/src/PoliciesPage.test.tsx web/src/RolesPage.test.tsx web/src/UsersPage.test.tsx web/src/configForms.test.ts web/index.html web/nginx.conf
git commit -m "fix: harden admin console auth and secret editing"
```

### Task 5: Remove policy priority from models, APIs, UI, and migrations

**AC IDs:** AC-013

**Files:**
- Modify: `src/adg/control_plane/models/governance.py`
- Modify: `src/adg/admin_api/console.py`
- Modify: `src/adg/policy/runtime.py`
- Modify: `tests/unit/policy/test_runtime_policy.py`
- Modify: `tests/integration/test_admin_console_api.py`
- Modify: `web/src/main.tsx`
- Modify: `src/adg/control_plane/migrations/versions/202604260001_directory_runtime_baseline.py`
- Create: `src/adg/control_plane/migrations/versions/202604260002_security_hardening_runtime_admin.py`

- [ ] **Step 1: Add failing tests that assert policy payloads no longer expose `priority`.**

```python
def test_resource_policy_api_payload_omits_priority() -> None:
    response = client.get("/admin/resource-policies", headers=auth())
    assert "priority" not in response.json()[0]
```

Also add/update unit tests to keep deny-before-allow semantics without any priority ordering.

- [ ] **Step 2: Run the policy/admin tests and verify they fail.**

Run:
- `uv run --extra dev pytest tests/unit/policy/test_runtime_policy.py -v`
- `uv run --extra dev pytest tests/integration/test_admin_console_api.py -v`

Expected: failures because payloads still include `priority` and the schema still expects it.

- [ ] **Step 3: Remove `priority` end-to-end and add the migration that drops the columns.**

```python
with op.batch_alter_table("resource_policies") as batch_op:
    batch_op.drop_column("priority")

with op.batch_alter_table("field_policies") as batch_op:
    batch_op.drop_column("priority")
```

Update Pydantic models, serializers, UI forms, and API tests to match the simpler contract.

- [ ] **Step 4: Re-run the policy/admin tests and verify they pass.**

Run the same commands from Step 2.

Expected: all updated policy and admin console tests pass.

- [ ] **Step 5: Commit the policy-simplification change set.**

```bash
git add src/adg/control_plane/models/governance.py src/adg/admin_api/console.py src/adg/policy/runtime.py tests/unit/policy/test_runtime_policy.py tests/integration/test_admin_console_api.py web/src/main.tsx src/adg/control_plane/migrations/versions/202604260001_directory_runtime_baseline.py src/adg/control_plane/migrations/versions/202604260002_security_hardening_runtime_admin.py
git commit -m "refactor: remove policy priority"
```

### Task 6: Split audit summary from raw-SQL detail and audit SQL-view reads

**AC IDs:** AC-014, AC-015

**Files:**
- Modify: `src/adg/audit/models.py`
- Modify: `src/adg/audit/service.py`
- Modify: `src/adg/admin_api/console.py`
- Modify: `tests/integration/test_admin_console_api.py`
- Modify: `web/src/main.tsx`

- [ ] **Step 1: Add failing integration tests for audit summary responses and raw-SQL detail retrieval auditing.**

```python
def test_audit_event_list_omits_raw_sql_by_default() -> None:
    response = client.get("/admin/audit-events", headers=auth())
    assert "sql_text" not in response.json()[0]


def test_audit_event_raw_sql_detail_is_separately_audited() -> None:
    response = client.get("/admin/audit-events/event_1/sql", headers=auth())
    assert response.json()["sql_text"] == "select id from public.customers limit 1"
    events = client.get("/admin/audit-events", headers=auth()).json()
    assert any(event["event_type"] == "audit_sql_view" for event in events)
```

- [ ] **Step 2: Run the audit/admin tests and verify they fail.**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py -v`

Expected: failures because audit list responses still include `sql_text` and no detail endpoint exists.

- [ ] **Step 3: Implement audit summary/detail separation.**

```python
@router.get("/audit-events/{event_id}/sql")
def get_audit_event_sql(...):
    ...
    AuditService(session).record_event(
        user_id=None,
        api_key_id=api_key.id,
        event_type="audit_sql_view",
        decision="allowed",
        datasource_id=event.datasource_id,
        resource_ids=json.loads(event.resource_ids_json),
        query_id=event.query_id,
        sql_text=None,
        reason=None,
        metadata={"target_event_id": event.id},
    )
```

Also update the main audit list serializer to omit `sql_text` and move raw SQL viewing to a dedicated UI action.

- [ ] **Step 4: Re-run the audit/admin tests and verify they pass.**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py -v`

Expected: the new audit summary/detail tests pass.

- [ ] **Step 5: Commit the audit exposure hardening change set.**

```bash
git add src/adg/audit/models.py src/adg/audit/service.py src/adg/admin_api/console.py tests/integration/test_admin_console_api.py web/src/main.tsx
git commit -m "fix: limit default audit sql exposure"
```

### Task 7: End-to-end verification

**AC IDs:** AC-001 through AC-016

**Files:**
- Modify: any files touched by previous tasks only if verification exposes defects

- [ ] **Step 1: Run the full backend verification suite.**

Run:
- `uv run --extra dev pytest`
- `uv run --extra dev ruff check .`
- `uv run --extra dev mypy src tests`

Expected: all commands exit successfully.

- [ ] **Step 2: Run the full frontend verification suite.**

Run:
- `npm test`
- `npm run build`

Expected: all frontend tests pass and the production build succeeds.

- [ ] **Step 3: Run focused regression commands for the security-critical areas.**

Run:
- `uv run --extra dev pytest tests/unit/sql_guard/test_guard.py tests/unit/gateway_runtime/test_tools.py tests/unit/control_plane/test_datasource_service.py tests/integration/test_admin_datasources.py tests/integration/test_admin_console_api.py -v`
- `npm test`

Expected: the regression-focused suite passes without failures.

- [ ] **Step 4: Inspect the final diff and confirm only intended files changed.**

Run: `git status --short`

Expected: only planned source, test, migration, and doc files appear modified or added.

- [ ] **Step 5: Prepare for code review and acceptance testing.**

```bash
git add .
git status --short
```

Expected: the branch is ready for review tooling with all intended changes staged or intentionally unstaged.
