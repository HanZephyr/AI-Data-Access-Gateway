# User Directory and Runtime Identity Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace caller-supplied runtime identity with user-bound runtime API keys, add enterprise directory management to the admin console, and restart the database migration baseline around the new model.

**Architecture:** Introduce a first-class directory layer (`users`, `roles`, `org_nodes`, `user_roles`) inside the control plane, bind runtime API keys directly to users, and derive runtime identity entirely from authenticated key lookups. Refactor admin APIs and console pages to manage users, roles, organization hierarchy, and imports from a unified operator workflow while removing runtime identity fields from all public tool contracts.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TypeScript, Ant Design, Vite, pytest, mypy, ruff, Vitest

---

### Task 1: Reset the control-plane schema around directory entities

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\models\api_key.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\models\directory.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\models\__init__.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\migrations\versions\202604260001_directory_runtime_baseline.py`
- Delete/replace: existing legacy Alembic revisions under `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\migrations\versions\`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_migrations.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\control_plane\test_api_key_model.py`

- [ ] **Step 1: Write the failing schema tests**

```python
def test_directory_tables_exist_after_migration() -> None:
    tables = migrated_table_names()
    assert "users" in tables
    assert "roles" in tables
    assert "user_roles" in tables
    assert "org_nodes" in tables


def test_api_keys_table_has_user_id_column() -> None:
    columns = migrated_columns("api_keys")
    assert "user_id" in columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/integration/test_migrations.py tests/unit/control_plane/test_api_key_model.py -v`
Expected: FAIL because the new directory tables and `api_keys.user_id` do not exist yet.

- [ ] **Step 3: Define the new SQLAlchemy models and clean Alembic baseline**

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_node_id: Mapped[str | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True)
    external_ref: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Role(Base):
    __tablename__ = "roles"
```

```python
def upgrade() -> None:
    op.create_table("org_nodes", ...)
    op.create_table("users", ...)
    op.create_table("roles", ...)
    op.create_table("user_roles", ...)
    op.add_column("api_keys", sa.Column("user_id", sa.String(length=36), nullable=True))
```

- [ ] **Step 4: Run tests to verify the schema passes**

Run: `uv run --extra dev pytest tests/integration/test_migrations.py tests/unit/control_plane/test_api_key_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/models/api_key.py src/adg/control_plane/models/directory.py src/adg/control_plane/models/__init__.py src/adg/control_plane/migrations/versions tests/integration/test_migrations.py tests/unit/control_plane/test_api_key_model.py
git commit -m "feat: add directory schema baseline"
```

### Task 2: Add directory services and user-bound runtime key lifecycle

**Files:**
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\services\directory_service.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\services\api_key_service.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\bootstrap.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\control_plane\test_directory_service.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_admin_bootstrap.py`

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_create_user_generates_one_runtime_key(db_session: Session) -> None:
    user, plaintext = DirectoryService(db_session).create_user(
        name="Alice",
        external_ref="u001",
        org_node_id=None,
        role_ids=[],
    )
    assert plaintext.startswith("adg_")
    assert active_runtime_key_for_user(db_session, user.id) is not None


def test_reset_user_key_revokes_old_key(db_session: Session) -> None:
    service = DirectoryService(db_session)
    user, old_key = service.create_user(name="Alice", external_ref="u001", org_node_id=None, role_ids=[])
    new_key = service.reset_runtime_key(user.id)
    assert verify_runtime_key(old_key) is False
    assert verify_runtime_key(new_key) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_directory_service.py tests/integration/test_admin_bootstrap.py -v`
Expected: FAIL because `DirectoryService` and bound-key lifecycle do not exist.

- [ ] **Step 3: Implement minimal directory and key lifecycle service**

```python
class DirectoryService:
    def create_user(self, *, name: str, external_ref: str, org_node_id: str | None, role_ids: list[str]) -> tuple[User, str]:
        user = User(name=name, external_ref=external_ref, org_node_id=org_node_id, status="active")
        self._session.add(user)
        self._session.flush()
        self._assign_roles(user.id, role_ids)
        _, plaintext = create_api_key(self._session, name=f"user:{user.name}", scopes=["runtime"], user_id=user.id)
        return user, plaintext
```

```python
def create_api_key(..., user_id: str | None = None) -> tuple[ApiKey, str]:
    record = ApiKey(..., user_id=user_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_directory_service.py tests/integration/test_admin_bootstrap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/services/directory_service.py src/adg/control_plane/services/api_key_service.py src/adg/control_plane/bootstrap.py tests/unit/control_plane/test_directory_service.py tests/integration/test_admin_bootstrap.py
git commit -m "feat: add user-bound runtime key lifecycle"
```

### Task 3: Replace runtime request identity with key-derived identity

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\app\dependencies.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\policy\runtime.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\gateway_runtime\tools.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\mcp_api\runtime_tools.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\mcp_server\server.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\mcp_api\tools.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_mcp_tools_api.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_mcp_streamable_http.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\policy\test_runtime_policy.py`

- [ ] **Step 1: Write failing runtime identity tests**

```python
def test_runtime_tool_rejects_request_identity_fields(client: TestClient) -> None:
    response = client.post(
        "/api/tools/list_datasources",
        json={"user_id": "spoofed"},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )
    assert response.status_code == 422


def test_runtime_identity_is_loaded_from_key_binding(db_session: Session) -> None:
    identity = load_runtime_identity(db_session, raw_api_key="adg_runtime")
    assert identity.user_id == "user_1"
    assert identity.role_ids == ["role_finance"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/integration/test_mcp_tools_api.py tests/integration/test_mcp_streamable_http.py tests/unit/policy/test_runtime_policy.py -v`
Expected: FAIL because runtime tools still accept request identity fields and identity is not key-derived.

- [ ] **Step 3: Implement key-derived runtime identity and remove external identity inputs**

```python
@dataclass(frozen=True)
class RuntimeIdentity:
    user_id: str
    role_ids: list[str]
    org_node_id: str | None


def authenticate_runtime_api_key_value(...) -> AuthenticatedRuntimeKey:
    ...
    if api_key.user_id is None:
        raise HTTPException(status_code=403, detail="Runtime key must be bound to a user")
```

```python
def dispatch_runtime_tool_call(..., payload: dict[str, Any], runtime_identity: RuntimeIdentity, ...) -> dict[str, Any]:
    forbidden = {"user_id", "roles", "groups"} & payload.keys()
    if forbidden:
        raise HTTPException(status_code=422, detail="Runtime identity fields are not accepted")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/integration/test_mcp_tools_api.py tests/integration/test_mcp_streamable_http.py tests/unit/policy/test_runtime_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/app/dependencies.py src/adg/policy/runtime.py src/adg/gateway_runtime/tools.py src/adg/mcp_api/runtime_tools.py src/adg/mcp_server/server.py src/adg/mcp_api/tools.py tests/integration/test_mcp_tools_api.py tests/integration/test_mcp_streamable_http.py tests/unit/policy/test_runtime_policy.py
git commit -m "feat: derive runtime identity from bound api keys"
```

### Task 4: Narrow policy and masking subjects to all, user, and role

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\admin_api\console.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\masking\service.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\policy\runtime.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_admin_console_api.py`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\masking\test_service.py`

- [ ] **Step 1: Write failing subject validation tests**

```python
def test_policy_creation_rejects_group_subject(client: TestClient) -> None:
    response = client.post(
        "/admin/resource-policies",
        json={"subject_type": "group", "subject_id": "finance", ...},
        headers=admin_auth(),
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py tests/unit/masking/test_service.py -v`
Expected: FAIL because `group` is still accepted.

- [ ] **Step 3: Implement subject validation and remove group matching**

```python
VALID_SUBJECT_TYPES = {"all", "user", "role"}

def _validate_subject_type(subject_type: str) -> None:
    if subject_type not in VALID_SUBJECT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported subject type")
```

```python
if policy.subject_type == "role":
    return policy.subject_id in identity.role_ids
return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py tests/unit/masking/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api/console.py src/adg/masking/service.py src/adg/policy/runtime.py tests/integration/test_admin_console_api.py tests/unit/masking/test_service.py
git commit -m "feat: restrict governance subjects to users and roles"
```

### Task 5: Add admin APIs for users, roles, organization nodes, and user key reset

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\admin_api\console.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_admin_directory_api.py`

- [ ] **Step 1: Write failing admin directory API tests**

```python
def test_admin_can_create_user_and_receive_plaintext_key(client: TestClient) -> None:
    response = client.post(
        "/admin/users",
        json={"name": "Alice", "external_ref": "u001", "org_node_id": None, "role_ids": []},
        headers=admin_auth(),
    )
    assert response.status_code == 201
    assert response.json()["api_key"].startswith("adg_")


def test_admin_can_reset_user_key(client: TestClient) -> None:
    response = client.post("/admin/users/user_1/reset-key", headers=admin_auth())
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/integration/test_admin_directory_api.py -v`
Expected: FAIL because the user, role, organization, and key reset APIs do not exist yet.

- [ ] **Step 3: Implement the admin directory endpoints**

```python
@router.post("/users")
def create_user(...):
    user, plaintext = DirectoryService(session).create_user(...)
    return {"id": user.id, "name": user.name, "api_key": plaintext, ...}


@router.post("/users/{user_id}/reset-key")
def reset_user_key(...):
    plaintext = DirectoryService(session).reset_runtime_key(user_id)
    return {"api_key": plaintext}
```

```python
@router.get("/roles")
def list_roles(...): ...


@router.get("/org-nodes")
def list_org_nodes(...): ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/integration/test_admin_directory_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api/console.py tests/integration/test_admin_directory_api.py
git commit -m "feat: add admin directory management apis"
```

### Task 6: Build import pipeline and Excel import preview/execute flow

**Files:**
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\models.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\excel.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\pipeline.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\admin_api\console.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\control_plane\test_import_pipeline.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_admin_import_api.py`

- [ ] **Step 1: Write failing import tests**

```python
def test_excel_preview_creates_missing_org_nodes_and_roles(db_session: Session) -> None:
    result = preview_excel_import(
        rows=[{"user_name": "Alice", "org_path": "Company/Finance", "external_ref": "u001", "roles": "Analyst"}],
        delimiter="/",
    )
    assert result.org_nodes_to_create == ["Company", "Company/Finance"]
    assert result.roles_to_create == ["Analyst"]


def test_empty_org_path_maps_user_to_root(db_session: Session) -> None:
    result = execute_import(...)
    assert loaded_user.org_node_id == root_org_node_id(db_session)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_import_pipeline.py tests/integration/test_admin_import_api.py -v`
Expected: FAIL because no import pipeline exists.

- [ ] **Step 3: Implement normalized import pipeline and admin endpoints**

```python
@dataclass
class ImportedUserRow:
    user_name: str
    org_path: str | None
    external_ref: str
    roles: list[str]
```

```python
def normalize_org_path(raw: str | None, delimiter: str) -> list[str]:
    if not raw:
        return []
    return [segment.strip() for segment in raw.split(delimiter) if segment.strip()]
```

```python
@router.post("/users/imports/excel/preview")
def preview_users_excel_import(...): ...

@router.post("/users/imports/excel/execute")
def execute_users_excel_import(...): ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_import_pipeline.py tests/integration/test_admin_import_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/imports src/adg/admin_api/console.py tests/unit/control_plane/test_import_pipeline.py tests/integration/test_admin_import_api.py
git commit -m "feat: add excel directory import pipeline"
```

### Task 7: Add pluggable third-party importer connector interface

**Files:**
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\connectors\base.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\connectors\registry.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\connectors\feishu.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\connectors\wecom.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\control_plane\imports\connectors\dingtalk.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\admin_api\console.py`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\unit\control_plane\test_import_connectors.py`

- [ ] **Step 1: Write failing connector normalization tests**

```python
def test_feishu_connector_normalizes_users_and_org_paths() -> None:
    connector = FeishuImporter(...)
    payload = connector.normalize(sample_feishu_response())
    assert payload.users[0].external_ref == "ou_123"
    assert payload.users[0].org_path == "Company/Finance"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_import_connectors.py -v`
Expected: FAIL because the importer connector interface does not exist.

- [ ] **Step 3: Implement the connector abstraction and manual import entrypoint**

```python
class DirectoryImporter(Protocol):
    def fetch(self, config: dict[str, Any]) -> DirectoryImportBatch: ...


CONNECTOR_REGISTRY = {
    "feishu": FeishuImporter,
    "wecom": WeComImporter,
    "dingtalk": DingTalkImporter,
}
```

```python
@router.post("/users/importers/{platform}/pull")
def pull_import_from_platform(platform: str, ...):
    connector = CONNECTOR_REGISTRY[platform](...)
    batch = connector.fetch(config)
    return preview_and_stage(batch)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/unit/control_plane/test_import_connectors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/control_plane/imports/connectors src/adg/admin_api/console.py tests/unit/control_plane/test_import_connectors.py
git commit -m "feat: add pluggable directory importer connectors"
```

### Task 8: Rebuild the admin console around users, roles, and import flows

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\main.tsx`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\styles.css`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\directoryForms.ts`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\directoryForms.test.ts`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\UsersPage.test.tsx`
- Create: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\RolesPage.test.tsx`

- [ ] **Step 1: Write failing console tests**

```tsx
it("shows a users navigation item and no standalone organization page", async () => {
  render(<AppShell />);
  expect(screen.getByText("Users")).toBeInTheDocument();
  expect(screen.queryByText("Organization")).not.toBeInTheDocument();
});

it("opens excel import modal with click and drag upload affordances", async () => {
  render(<UsersPage />);
  await user.click(screen.getByRole("button", { name: "Import Excel" }));
  expect(screen.getByText("Upload file")).toBeInTheDocument();
  expect(screen.getByText("Drag file here")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix web -- UsersPage.test.tsx RolesPage.test.tsx directoryForms.test.ts`
Expected: FAIL because the users page, roles page, and import modal do not exist yet.

- [ ] **Step 3: Implement the new console pages and flows**

```tsx
const adminPages = [
  { key: "overview", label: t("nav.overview") },
  { key: "users", label: t("nav.users") },
  { key: "roles", label: t("nav.roles") },
  ...
];
```

```tsx
function UsersPage() {
  return (
    <div className="directory-workspace">
      <aside className="directory-tree-pane">{/* org tree */}</aside>
      <section className="directory-users-pane">{/* table + detail drawer + import modal */}</section>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test --prefix web -- UsersPage.test.tsx RolesPage.test.tsx directoryForms.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/main.tsx web/src/styles.css web/src/directoryForms.ts web/src/directoryForms.test.ts web/src/UsersPage.test.tsx web/src/RolesPage.test.tsx
git commit -m "feat: add admin directory console"
```

### Task 9: Update MCP setup guidance and runtime examples for the new identity contract

**Files:**
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\src\adg\admin_api\console.py`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\mcpGuides.ts`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\mcpGuides.test.ts`
- Modify: `D:\Projects\personalProjects\AI-Data-Access-Gateway\web\src\main.tsx`
- Test: `D:\Projects\personalProjects\AI-Data-Access-Gateway\tests\integration\test_admin_console_api.py`

- [ ] **Step 1: Write failing documentation tests**

```python
def test_admin_mcp_setup_does_not_reference_request_identity_fields(client: TestClient) -> None:
    body = client.get("/admin/mcp/setup", headers=admin_auth()).json()
    assert "user_id" not in json.dumps(body)
    assert "roles" not in json.dumps(body)
    assert "groups" not in json.dumps(body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py -v`
Expected: FAIL because current MCP setup copy still references request-supplied identity behavior.

- [ ] **Step 3: Implement the new guidance copy and tool schemas**

```ts
export function buildMcpPlatformGuides(setup: McpSetupPayload): McpPlatformGuide[] {
  return [
    {
      key: "codex",
      snippets: [
        {
          label: "config.toml",
          language: "toml",
          code: [
            "[mcp_servers.adg]",
            'enabled = true',
            `url = "${setup.server_url}"`,
            "",
            "[mcp_servers.adg.http_headers]",
            `${setup.api_key_header} = "\\${ADG_RUNTIME_API_KEY}"`,
          ].join("\\n"),
        },
      ],
    },
  ];
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/integration/test_admin_console_api.py -v && npm test --prefix web -- mcpGuides.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adg/admin_api/console.py web/src/mcpGuides.ts web/src/mcpGuides.test.ts web/src/main.tsx tests/integration/test_admin_console_api.py
git commit -m "docs: update mcp guidance for key-derived identity"
```

### Task 10: Final verification, browser coverage, and docs cleanup

**Files:**
- Modify as needed: `D:\Projects\personalProjects\AI-Data-Access-Gateway\README.md`
- Modify as needed: `D:\Projects\personalProjects\AI-Data-Access-Gateway\examples\seed_demo.py`
- Test: full backend and frontend suites

- [ ] **Step 1: Write the final verification checklist into the working notes**

```text
- create user and view one-time key
- reset key and verify old key fails
- disable user and verify runtime rejection
- create role and assign to user
- create user-subject and role-subject policies
- import Excel with empty org path and missing roles
- open MCP setup and verify no caller identity fields
```

- [ ] **Step 2: Run the full automated verification**

Run: `uv run --extra dev pytest && uv run --extra dev ruff check src tests examples && uv run --extra dev mypy src tests && npm test --prefix web && npm run build --prefix web`
Expected: all commands succeed

- [ ] **Step 3: Run browser verification**

```text
Open the admin console, log in as admin, navigate Users/Roles/Policies/MCP Setup, and execute the acceptance checklist manually with browser tooling.
```

- [ ] **Step 4: Update any remaining operator docs to match the new model**

```markdown
- runtime keys are user-bound
- user directory is managed from the admin console
- direct runtime HTTP calls use /api/tools/{tool_name}
- organization does not participate in authorization
```

- [ ] **Step 5: Commit**

```bash
git add README.md examples/seed_demo.py
git commit -m "chore: finalize user directory redesign docs and verification"
```

---

## Self-Review

### Spec coverage

- Directory schema reset is covered by Task 1.
- User-bound runtime key lifecycle is covered by Task 2.
- Key-derived runtime identity is covered by Task 3.
- Policy subject narrowing is covered by Task 4.
- Admin APIs for users, roles, organization, and key reset are covered by Task 5.
- Excel import and root-path behavior are covered by Task 6.
- Pluggable third-party importers are covered by Task 7.
- Users/Roles console UX and import modal are covered by Task 8.
- MCP setup guidance update is covered by Task 9.
- Final verification and operator docs are covered by Task 10.

### Placeholder scan

- No `TODO`, `TBD`, or deferred code placeholders remain in task steps.
- Each task contains explicit files, tests, commands, and expected outcomes.

### Type consistency

- Runtime identity naming is consistent across tasks as `RuntimeIdentity` with `user_id`, `role_ids`, and `org_node_id`.
- Directory models are consistently named `User`, `Role`, `OrgNode`, and `user_roles`.
- Admin API routes are consistently described under `/admin/users`, `/admin/roles`, `/admin/org-nodes`, and `/admin/users/imports/...`.
