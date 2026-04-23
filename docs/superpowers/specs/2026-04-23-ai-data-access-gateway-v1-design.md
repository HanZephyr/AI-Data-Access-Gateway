# AI Data Access Gateway V1 Design

Date: 2026-04-23

## 1. Positioning

AI Data Access Gateway is an open-source secure database access gateway for AI Agents. It sits between AI Agents and real databases, exposing controlled metadata discovery and read-only query execution while enforcing authorization, SQL safety checks, masking, reversible desensitization, internal decryption, and audit logging.

The project is not a BI platform, reporting system, dashboard product, data visualization tool, ETL platform, or enterprise user center. Its responsibility is the governed data access layer for AI.

V1 focuses on an open-source usable MVP: simple enough for individual developers and small teams to deploy, while keeping architecture boundaries ready for later enterprise-oriented capabilities.

## 2. V1 Product Scope

V1 must provide:

- A single FastAPI service.
- MCP tools for AI Agent access.
- Admin REST APIs for the web console.
- Internal HTTP APIs for trusted backend operations such as decryption.
- SQLite as the default control-plane database.
- Lightweight relational connectors for PostgreSQL, MySQL, and Doris, with database driver dependencies installed through optional extras.
- Metadata scanning for relational databases.
- Resource-level tags.
- API Key plus identity context authorization.
- Resource-level access policies.
- Field-level allow and deny policies.
- Conservative SQL Guard based on AST parsing.
- Read-only query execution.
- Fixed, partial, hash, and reversible masking.
- Reversible masking values encoded as `$adg_rev$<decrypt_context_id>$<ciphertext>`.
- Decrypt contexts stored in the control-plane database.
- Audit logs.
- React + Vite + TypeScript + Ant Design web console.
- Local quickstart, MCP setup documentation, and demo examples.

V1 explicitly excludes:

- Login system, OAuth, and JWT-based identity.
- External JWT Mode.
- Row-level access policies.
- AI review layer for query risk assessment.
- BI reports, dashboards, and business analytics UI.
- Independent connector packages.
- Redis as a required dependency.
- Multi-service deployment.
- Open-core or commercial-edition boundary design.

## 3. Architecture

V1 uses a single FastAPI service with internal layered modules. One process exposes three entry surfaces:

```text
AI Agent / MCP Client
  -> MCP Server

Web Console
  -> Admin REST API

Trusted Backend / Internal Service
  -> Internal HTTP API
```

Internal modules:

```text
adg
  ├─ app
  ├─ mcp
  ├─ admin_api
  ├─ internal_api
  ├─ gateway_runtime
  ├─ control_plane
  ├─ connectors
  ├─ policy
  ├─ sql_guard
  ├─ masking
  ├─ audit
  └─ shared
```

The design keeps deployment simple while preserving future split points. Later versions may split MCP Runtime and Control Plane, add Redis for decrypt context storage, support external identity, add non-relational data sources, or introduce an AI review layer without rewriting the V1 core.

## 4. Repository Structure

The initial repository should use this structure:

```text
AI-Data-Access-Gateway/
  ├─ pyproject.toml
  ├─ README.md
  ├─ LICENSE
  ├─ .env.example
  ├─ src/
  │  └─ adg/
  │     ├─ app/
  │     │  ├─ main.py
  │     │  ├─ settings.py
  │     │  ├─ dependencies.py
  │     │  └─ lifecycle.py
  │     ├─ mcp/
  │     │  ├─ server.py
  │     │  ├─ tools.py
  │     │  └─ schemas.py
  │     ├─ admin_api/
  │     ├─ internal_api/
  │     ├─ gateway_runtime/
  │     │  ├─ query_service.py
  │     │  ├─ metadata_service.py
  │     │  └─ schemas.py
  │     ├─ control_plane/
  │     │  ├─ models/
  │     │  ├─ repositories/
  │     │  ├─ services/
  │     │  └─ migrations/
  │     ├─ connectors/
  │     │  ├─ base.py
  │     │  ├─ registry.py
  │     │  ├─ relational.py
  │     │  ├─ postgres/
  │     │  ├─ mysql/
  │     │  └─ doris/
  │     ├─ policy/
  │     ├─ sql_guard/
  │     ├─ masking/
  │     ├─ audit/
  │     └─ shared/
  ├─ web/
  │  └─ console/
  ├─ tests/
  │  ├─ unit/
  │  ├─ integration/
  │  └─ fixtures/
  ├─ docs/
  │  ├─ architecture/
  │  ├─ mcp-tools/
  │  ├─ deployment/
  │  └─ superpowers/
  └─ dev-docs/
```

Module boundaries:

- `mcp` defines tools, validates tool inputs, formats AI-facing responses, and calls `gateway_runtime`.
- `gateway_runtime` orchestrates metadata discovery and query execution. It does not own SQL safety, policy, masking, connector, or audit internals.
- `control_plane` owns governance configuration, metadata snapshots, policies, API keys, and decrypt contexts.
- `connectors` are thin adapters. They test connections, scan metadata, execute read-only queries, normalize result types, and declare dialects.
- `policy` makes authorization decisions.
- `sql_guard` parses SQL, checks safety, and extracts accessed resources and fields.
- `masking` applies masking and reversible desensitization, and handles internal decryption.
- `audit` records structured events.
- `shared` contains common errors, value objects, encryption helpers, pagination, and time utilities.

## 5. Connector Strategy

Connectors are integrated in the main service repository. They are not independent packages in V1. The plugin-like behavior is limited to optional driver dependencies:

```bash
pip install ai-data-access-gateway[postgres]
pip install ai-data-access-gateway[mysql]
pip install ai-data-access-gateway[doris]
pip install ai-data-access-gateway[all]
```

Each connector implements a small interface:

```text
test_connection
scan_metadata
execute_readonly_query
dialect_name
normalize_result
```

If a datasource type is configured but its driver dependency is unavailable, the service returns a clear connector-not-installed error.

Although V1 supports relational databases first, connector abstractions must not assume all future data sources are SQL databases. Core names should use `datasource`, `resource`, `entity`, and `field` where appropriate. SQL-specific behavior stays inside relational connectors and `sql_guard`.

## 6. MCP Tools

The MCP surface must stay lightweight and stable. AI should not need to understand internal policy details, connector differences, or separate tools for every database type.

V1 exposes these tools:

```text
list_datasources
list_tags
list_resources
list_resources_by_tag
describe_resource
preview_resource
execute_query
```

`list_datasources` returns data sources visible to the current identity context.

`list_tags` returns resource-level tags visible to the current identity context. It must not leak tags that only exist on resources the user cannot discover.

`list_resources` returns accessible resources under a datasource.

`list_resources_by_tag` returns accessible resources matching one or more tags. Tags are resource-level only.

`describe_resource` returns resource structure. For relational tables and views, the AI-facing response should use familiar fields such as `columns`, `data_type`, `nullable`, `access`, and `masking_strategy`.

`preview_resource` returns a small masked preview and records audit events.

`execute_query` accepts:

```json
{
  "user_id": "u_123",
  "tenant_id": "t_001",
  "datasource_id": "ds_01",
  "query_language": "sql",
  "resource_ids": ["res_01", "res_02"],
  "query": "select ...",
  "limit": 100
}
```

`resource_ids` are an AI-declared intent scope. They are used for the first scope check and audit context, but final validation depends on SQL AST extraction and policy checks.

The query response should remain easy for AI to process:

```json
{
  "query_id": "qry_123",
  "status": "success",
  "columns": [
    {"name": "customer_name", "data_type": "varchar"},
    {"name": "total_amount", "data_type": "decimal"}
  ],
  "rows": [
    {
      "customer_name": "$adg_rev$ctx_456$ciphertext",
      "total_amount": 1200.5
    }
  ],
  "masking": {
    "masked_columns": [
      {
        "name": "customer_name",
        "strategy": "reversible",
        "marker": "$adg_rev$"
      }
    ]
  },
  "warnings": []
}
```

Future data source types should reuse these tools where possible. New capabilities should be expressed through `type`, `kind`, `query_language`, and `capabilities` before adding more tools.

## 7. Control Plane Data Model

The control plane stores governance configuration in a relational database. SQLite is the V1 default.

### Identity and API Keys

```text
api_keys
  id
  name
  key_hash
  status
  scopes
  expires_at
  created_at

users
  id
  tenant_id
  external_user_id
  display_name
  status

roles
user_roles
groups
user_groups
```

V1 does not provide a login system. Callers authenticate with an API key and pass identity context values such as `user_id`, `tenant_id`, `roles`, and `groups`.

### Datasources and Resources

```text
datasources
  id
  tenant_id
  name
  type
  datasource_kind
  config_encrypted
  status
  created_at

resources
  id
  tenant_id
  datasource_id
  parent_id
  kind
  name
  path
  display_name
  query_language
  metadata_json
  scanned_at

resource_fields
  id
  tenant_id
  datasource_id
  resource_id
  name
  data_type
  nullable
  ordinal_position
  description
  metadata_json
```

For relational databases:

```text
database/catalog -> resource(kind=database)
schema           -> resource(kind=schema)
table/view       -> resource(kind=relational_table / relational_view)
column           -> resource_fields
```

### Tags

```text
tags
  id
  tenant_id
  name
  category
  description

resource_tags
  id
  tenant_id
  tag_id
  resource_id
```

Tags do not bind to fields or columns. They bind only to datasource, database/catalog, schema/namespace, table/view, collection, or entity-level resources.

Tags are for resource discovery, grouping, security classification, AI visibility grouping, and resource-level policy matching. Field governance is handled by field policies and masking policies.

### Policies

```text
resource_policies
  id
  tenant_id
  subject_type
  subject_id
  effect
  action
  resource_id nullable
  tag_id nullable
  priority
  status

field_policies
  id
  tenant_id
  subject_type
  subject_id
  effect
  resource_id
  field_name
  action
  priority
  status
```

Field policies only narrow access after resource-level access is granted. They cannot grant access to a field when the user lacks access to the parent resource.

### Masking and Decryption

```text
masking_policies
  id
  tenant_id
  resource_id
  field_name
  subject_type nullable
  subject_id nullable
  strategy
  config_json
  status

decrypt_contexts
  id
  tenant_id
  query_id
  user_id
  datasource_id
  key_ciphertext
  allowed_fields_json
  expires_at
  created_at
```

### Audit

```text
audit_events
  id
  tenant_id
  user_id
  api_key_id
  event_type
  datasource_id
  resource_ids_json
  query_id
  sql_text nullable
  decision
  reason nullable
  metadata_json
  created_at
```

Audit event types include metadata discovery, query execution, SQL rejection, permission rejection, masking, decryption, connection test, and admin policy changes.

## 8. Authorization Model

V1 uses API Key plus identity context:

```text
X-ADG-API-Key: <gateway-api-key>
```

Request body or MCP arguments provide:

```text
user_id
tenant_id
roles
groups
```

The gateway trusts identity context only from callers that hold a valid API key. This avoids implementing login, OAuth, or JWT in V1 while preventing completely unauthenticated identity spoofing.

Authorization order:

```text
datasource permission
  -> resource/table permission
  -> field access policy
  -> masking policy
```

Upper-level denial cannot be overridden by lower-level allow rules. Field policy and masking policy only narrow, hide, or transform data after resource access has already been granted.

## 9. SQL Guard

V1 SQL Guard is conservative and AST-based.

Allowed:

- `SELECT`
- `WITH`
- `JOIN`
- `WHERE`
- `GROUP BY`
- `HAVING`
- `ORDER BY`
- `LIMIT`
- Common aggregate functions such as `count`, `sum`, `avg`, `min`, and `max`.

Forbidden:

- Multiple statements.
- `INSERT`, `UPDATE`, `DELETE`, and `MERGE`.
- `CREATE`, `ALTER`, `DROP`, and `TRUNCATE`.
- Stored procedures.
- Transaction control.
- File reads, file writes, export commands, and external command execution.
- Non-whitelisted functions.
- AST nodes that V1 does not explicitly support.

SQL Guard returns a structured result:

```text
SqlGuardResult
  - allowed
  - normalized_sql
  - statement_type
  - accessed_resources
  - accessed_fields
  - used_functions
  - risk_level
  - rejection_reasons
  - warnings
```

SQL Guard does not make user authorization decisions. It only decides whether the SQL is structurally safe and identifies actual accessed resources and fields.

The execution pipeline is:

```text
execute_query
  -> API Key validation
  -> identity context parsing
  -> datasource and connector checks
  -> declared resource_ids quick check
  -> SQL AST parse
  -> SQL read-only and safety check
  -> actual resource and field extraction
  -> declared-vs-actual resource comparison
  -> policy check
  -> connector read-only execution
  -> masking
  -> audit
  -> response
```

Runtime safety limits:

- A query must have a limit, or the gateway injects a default limit.
- The effective limit cannot exceed `max_rows`.
- Query timeout is enforced.
- Read-only connection or read-only transaction is used when supported by the connector.
- Response size is limited.

Future versions may add `GuardProfile` values such as `conservative`, `balanced`, `advanced`, and `custom`. V1 only implements the conservative profile.

## 10. Masking and Reversible Desensitization

V1 supports:

```text
fixed
partial
hash
reversible
```

Masking is applied after connector execution and before returning data to AI.

For reversible masking:

1. Each query that hits reversible fields creates a decrypt context.
2. The service generates a query-level temporary encryption key.
3. Sensitive values are encrypted with the temporary key.
4. The temporary key is encrypted with the service-level secret and stored in `decrypt_contexts`.
5. The returned value is encoded as:

```text
$adg_rev$<decrypt_context_id>$<ciphertext>
```

The AI receives a normal string value plus masking metadata in the response. It does not receive the temporary key or plaintext.

## 11. Internal Decrypt API

Trusted internal services call the decrypt API with an API key:

```http
POST /internal/decrypt
X-ADG-API-Key: ...
```

Request:

```json
{
  "user_id": "u_123",
  "tenant_id": "t_001",
  "values": [
    "$adg_rev$ctx_456$ciphertext"
  ]
}
```

Flow:

```text
validate API Key
  -> parse $adg_rev$ marker and context id
  -> load decrypt_context
  -> validate TTL
  -> validate user_id, tenant_id, datasource_id, and allowed fields
  -> validate decrypt permission
  -> decrypt values
  -> write decrypt audit event
  -> return plaintext values
```

Expired contexts cannot be decrypted. V1 stores decrypt contexts in the control-plane database and uses a cleanup task to remove expired entries. Redis may be added later as an optional store.

## 12. Web Console and Admin API

The web console is a gateway control console, not a BI or analytics application.

Frontend stack:

```text
React + Vite + TypeScript + Ant Design
```

V1 pages:

- Data Sources
- Resource Explorer
- Tags
- Access Policies
- Field Policies
- Masking Policies
- API Keys
- Audit Logs
- MCP Setup

Ant Design should be used for standard admin UI elements such as tables, forms, filters, drawers, modals, tree views, selectors, tabs, and notifications. The project should avoid rebuilding generic admin components.

Admin API capabilities:

- Datasource CRUD.
- Connection testing.
- Metadata scan triggering.
- Resource and field browsing.
- Tag CRUD and resource tag binding.
- Resource policy management.
- Field policy management.
- Masking policy management.
- API key creation and revocation.
- Audit query.
- MCP setup metadata.

V1 management authentication can use an admin API key or bootstrap local administrator mode. A full login system is not part of V1.

## 13. Milestones

Milestone 1: Project skeleton and control-plane foundation

- FastAPI application.
- Settings.
- Database migrations.
- Base models.
- API Key validation.
- Audit foundation.

Milestone 2: Datasources and metadata scanning

- Connector base and registry.
- PostgreSQL, MySQL, and Doris thin adapters.
- Datasource CRUD.
- Metadata scanning.
- Resource and field snapshots.

Milestone 3: MCP query runtime

- `list_datasources`
- `list_tags`
- `list_resources`
- `list_resources_by_tag`
- `describe_resource`
- `preview_resource`
- `execute_query`
- SQL Guard.
- Resource and field policy checks.

Milestone 4: Masking and decryption

- Masking policies.
- Fixed, partial, hash, and reversible masking.
- Decrypt contexts.
- Internal decrypt API.
- Masking and decrypt audit events.

Milestone 5: Web console

- Ant Design control console.
- Datasource, resource, tag, policy, masking, API key, audit, and MCP setup pages.

Milestone 6: Documentation, demo, and tests

- README.
- Local quickstart.
- MCP client examples.
- Integration tests.
- Docker or docker compose demo.

## 14. Future Evolution

V1.1:

- Connector stability improvements.
- SQL Guard function whitelist expansion.
- Better audit filtering.
- PostgreSQL/MySQL support as control-plane databases.

V1.2:

- `GuardProfile` support.
- Optional Redis decrypt context store.
- More explicit policy conflict explanations.
- Admin configuration import and export.

V2:

- Signed identity context or External JWT Mode.
- Row-level policies.
- Optional AI review layer after SQL Guard and policy checks.
- Non-relational datasource connectors.
- Optional split between MCP Runtime and Control Plane.
