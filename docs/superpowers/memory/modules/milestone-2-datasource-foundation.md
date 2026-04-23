---
type: module_card
title: milestone-2-datasource-foundation
summary: Implemented datasource CRUD, connector registry, relational metadata scanning, and resource snapshot persistence for Milestone 2.
tags:
  - milestone-2
  - datasources
  - connectors
related_docs:
  - docs/superpowers/specs/2026-04-24-milestone-2-datasource-foundation-design.md
  - docs/superpowers/plans/2026-04-24-milestone-2-datasource-foundation.md
  - docs/superpowers/memory/modules/milestone-1-control-plane-foundation.md
last_verified_commit: 910c534
status: active
---

# Milestone 2 Datasource Foundation

## Responsibilities

- Persist datasource records and relational metadata snapshots in the control-plane database.
- Resolve connector implementations by datasource type through a shared registry.
- Provide admin CRUD plus datasource test and scan endpoints.
- Normalize relational metadata into deterministic `resources` and `resource_fields` snapshots.

## Entry points

- Admin datasource router: `src/adg/admin_api/datasources.py`
- Connector registry: `src/adg/connectors/registry.py`
- Relational connector base: `src/adg/connectors/relational.py`
- Datasource model: `src/adg/control_plane/models/datasource.py`
- Resource snapshot models: `src/adg/control_plane/models/resource.py`
- Datasource service: `src/adg/control_plane/services/datasource_service.py`
- Metadata scan service: `src/adg/control_plane/services/metadata_scan_service.py`
- Migration baseline: `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`

## Invariants

- Datasource CRUD and scan routes remain admin-only surfaces and must continue using `require_admin_api_key`.
- The control-plane schema now treats `datasources`, `resources`, and `resource_fields` as part of the baseline migration; later milestones should extend the same revision chain rather than reintroduce alternate bootstrap tables.
- `MetadataScanService.replace_snapshot()` must delete old field rows before resource rows, then insert the new snapshot in one transaction to avoid stale metadata.
- Connector resolution must fail with a stable domain error for unsupported connector types.
- Thin relational adapters are not the query runtime; in Milestone 2 they only support connection testing and metadata scanning.
- PostgreSQL, MySQL, and Doris driver availability is optional and missing-driver failures must name the required install extra.
- Relational snapshots use stable kinds: `database`, `schema`, `relational_table`, and `relational_view`.

## Extension points

- Milestone 3 should consume `datasources`, `resources`, and `resource_fields` for `list_datasources`, `list_resources`, `describe_resource`, and query runtime checks.
- Policy and tag milestones can attach their own lookup layers on top of these snapshot tables instead of inventing a second metadata store.
- Additional connectors can register through the same registry contract without changing admin route semantics.

## Common pitfalls

- Treating datasource `config_json` as encrypted storage. Milestone 2 persists plain JSON text and does not yet implement secret management.
- Assuming connector adapters should already execute user queries. Query execution is still deferred to Milestone 3.
- Appending snapshots without clearing old rows. This leaves stale schema artifacts behind and breaks later resource resolution.
- Hard-coding connector-specific behavior in the admin router. Connector branching belongs in the registry and adapter layer.
