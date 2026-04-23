# Milestone 2 Datasource Foundation Design

Date: 2026-04-24

## Scope

Milestone 2 implements the datasource and metadata scanning foundation described in the V1 design:

- Connector base contract and registry
- Thin PostgreSQL, MySQL, and Doris adapters
- Datasource persistence and admin CRUD
- Metadata scanning for relational datasources
- Resource and resource field snapshots

This milestone stays backend-only. It does not implement MCP runtime tools, SQL Guard, masking, decryption, or the web console.

## Goals

1. Operators can create, update, list, and delete datasource records through admin REST APIs.
2. The gateway can resolve a connector implementation by datasource type.
3. The gateway can scan relational metadata into control-plane snapshot tables.
4. Scan results are deterministic and replace prior snapshots for the same datasource.
5. Missing optional connector drivers fail with clear API errors instead of import crashes.

## Architecture

Milestone 2 extends the existing single FastAPI service with three focused layers:

- `control_plane.models` stores datasource, resource, and resource field snapshots.
- `connectors` defines the connector protocol, registry, and thin relational adapters.
- `admin_api.datasources` exposes admin CRUD and scan endpoints that orchestrate persistence and metadata scanning.

The admin API remains authenticated by admin-scoped API keys from Milestone 1. Connector instances stay thin: they validate driver availability, open SQLAlchemy engines, introspect relational metadata, and normalize results into shared snapshot shapes.

## Data Model

### Datasource

Add a `datasources` table with these fields:

- `id`: UUID string primary key
- `tenant_id`: tenant identifier
- `name`: operator-visible datasource name
- `type`: connector type such as `postgres`, `mysql`, or `doris`
- `datasource_kind`: `relational`
- `config_json`: JSON string for connection settings
- `status`: `active` or `disabled`
- `created_at`: timestamp
- `updated_at`: timestamp

V1 stores datasource config in plain JSON text inside SQLite for now. Encryption is deferred to a later milestone.

### Resource Snapshot

Add a `resources` table for scanned metadata:

- `id`
- `tenant_id`
- `datasource_id`
- `parent_id`
- `kind`
- `name`
- `path`
- `display_name`
- `query_language`
- `metadata_json`
- `scanned_at`

For relational datasources:

- database or catalog -> `kind="database"`
- schema -> `kind="schema"`
- table -> `kind="relational_table"`
- view -> `kind="relational_view"`

### Resource Field Snapshot

Add a `resource_fields` table:

- `id`
- `tenant_id`
- `datasource_id`
- `resource_id`
- `name`
- `data_type`
- `nullable`
- `ordinal_position`
- `description`
- `metadata_json`

## Connector Contract

Create a shared connector protocol that exposes:

- `connector_type`
- `test_connection(config)`
- `scan_metadata(config)`

`scan_metadata()` returns a normalized relational snapshot with:

- datasource kind
- databases
- schemas
- tables or views
- fields

The registry maps datasource type strings to connector classes. Unknown connector types return a domain error instead of a `KeyError`.

### Thin Relational Adapters

- PostgreSQL adapter uses SQLAlchemy URL building plus the PostgreSQL dialect.
- MySQL adapter uses SQLAlchemy URL building plus the MySQL dialect.
- Doris adapter reuses the MySQL driver path with a Doris connector type.

If the optional driver dependency is missing, adapters raise a connector-not-installed error with a message naming the extra the operator should install.

### Scanning Strategy

Use SQLAlchemy inspection APIs to collect:

- schemas
- tables
- views
- columns

Scan output should be normalized into a stable snapshot shape before persistence. Milestone 2 only needs relational metadata; row counts, sample data, tags, and policies are deferred.

## Admin API

Add `/admin/datasources` routes:

- `GET /admin/datasources`
- `POST /admin/datasources`
- `GET /admin/datasources/{datasource_id}`
- `PATCH /admin/datasources/{datasource_id}`
- `DELETE /admin/datasources/{datasource_id}`
- `POST /admin/datasources/{datasource_id}/test`
- `POST /admin/datasources/{datasource_id}/scan`

All routes require an admin-scoped API key.

### Request and Response Rules

- CRUD responses return stored datasource metadata but do not echo secrets beyond what is persisted in `config_json`.
- `test` returns `{ "status": "ok" }` on success.
- `scan` returns counts for scanned resources and fields.
- `delete` removes the datasource and any scanned snapshot rows for that datasource.

## Snapshot Persistence Rules

Scanning must replace prior snapshot rows for the datasource in one transaction:

1. Load datasource
2. Resolve connector
3. Fetch metadata snapshot
4. Delete old `resource_fields`
5. Delete old `resources`
6. Insert new `resources`
7. Insert new `resource_fields`
8. Commit

This keeps snapshots deterministic and avoids stale fields after schema changes.

## Error Handling

Expose stable API errors for:

- datasource not found
- connector type unsupported
- connector driver not installed
- connection test failure
- scan failure
- invalid datasource payload

Admin APIs may use `400`, `404`, or `409` where appropriate. Auth failures continue using Milestone 1 behavior.

## Testing

Milestone 2 needs:

- unit tests for connector registry and dependency errors
- unit tests for snapshot persistence service
- integration tests for datasource CRUD routes
- integration tests for scan route using a fake connector
- migration test updates covering new tables

## Out of Scope

- query execution
- SQL Guard
- tags and policies
- masking and decryption
- UI pages
- encrypted datasource config
