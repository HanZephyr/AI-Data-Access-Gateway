---
type: spec
title: user-directory-runtime-identity-redesign
summary: Replace request-supplied runtime identity with user-bound runtime API keys, enterprise directory management, and a user-centered admin console.
status: draft
---

# User Directory and Runtime Identity Redesign

## Objective

Refactor the control plane and runtime identity model so the product behaves like an administrator-managed enterprise directory gateway instead of a caller-supplied identity relay.

The new shape is:

- Only administrators manage the system.
- Ordinary users do not log in to this console.
- Each ordinary user owns exactly one active runtime API key.
- Runtime identity is derived only from `X-ADG-API-Key`.
- Runtime requests no longer supply `user_id`, `roles`, or `groups`.
- Authorization subjects are limited to `all`, `user`, and `role`.
- Organization structure is used for directory browsing, filtering, import, and audit context, but not for authorization.
- User and organization data can be imported from one Excel template or from pluggable third-party importer connectors.

This redesign replaces the current runtime identity contract rather than migrating it forward. Historical compatibility is out of scope.

## Non-goals

- No ordinary-user login flow.
- No ordinary-user self-service portal.
- No organization-node-based authorization.
- No bidirectional sync with Feishu, WeCom, DingTalk, or any other third-party directory.
- No attempt to preserve the current runtime request schema.
- No attempt to preserve existing Alembic history. Database migrations restart from a new baseline.

## Product Model

### System actors

- `Administrator`
  - Uses the admin console.
  - Manages datasources, resources, tags, policies, masking, users, roles, imports, audit, and system keys.
- `Ordinary user`
  - Does not use the admin console.
  - Receives one runtime API key from an administrator through an external channel.
  - Uses that key from an MCP client or direct HTTP tool caller.

### Identity model

Runtime identity is platform-owned, not caller-owned.

Every runtime request resolves identity as:

`API key -> bound user -> assigned roles -> organization node`

Only the platform computes this identity. Clients do not submit identity attributes.

### Authorization model

Policy subjects are restricted to:

- `all`
- `user`
- `role`

Organization nodes are not policy subjects. If an administrator wants department-level access behavior, they model that through roles.

## Domain Model

### users

Minimal user representation, limited to system-relevant fields:

- `id`
- `name`
- `org_node_id`
- `external_ref`
- `status`
- `created_at`
- `updated_at`

`external_ref` is the stable unique identifier from import sources such as Excel employee code or third-party platform user id. It exists to support idempotent import and avoid ambiguity for same-name users.

The system does not store email, phone, or unrelated enterprise profile data.

### roles

- `id`
- `name`
- `description`
- `status`
- `created_at`
- `updated_at`

### user_roles

- `user_id`
- `role_id`

One user may own multiple roles.

### org_nodes

- `id`
- `name`
- `code`
- `parent_id`
- `path`
- `depth`
- `status`
- `created_at`
- `updated_at`

`path` stores the canonical hierarchy path used for efficient search and display. Organization nodes exist for directory structure, not permissions.

### api_keys

Keep the table but change its responsibilities:

- add `user_id nullable`
- keep `scopes`
- keep `status`
- keep `expires_at`

Key categories:

- `admin` and `internal` keys:
  - system-level keys
  - `user_id` remains null
- `runtime` keys:
  - must bind to exactly one user

Invariant:

- one user may have only one active runtime key at a time

### Governance tables

Retain:

- `resource_policies`
- `field_policies`
- `masking_policies`

But narrow their valid `subject_type` values to:

- `all`
- `user`
- `role`

`group` is removed from the model.

## Runtime Contract

### Authentication

Runtime authentication continues to use:

- header: `X-ADG-API-Key`

But the resulting identity object changes.

Current runtime design trusts request payload identity. The new design does not.

### Runtime request contract

Runtime tools accept only business parameters.

Removed from both MCP tools and direct HTTP tools:

- `user_id`
- `roles`
- `groups`

Examples of retained parameters:

- `datasource_id`
- `resource_id`
- `tag_names`
- `query`
- `resource_ids`
- `limit`

### Runtime identity assembly

For each runtime request:

1. Authenticate API key.
2. Require `runtime` scope.
3. Resolve bound user from `api_keys.user_id`.
4. Load assigned roles from `user_roles`.
5. Load organization node from `users.org_node_id`.
6. Build internal identity context.
7. Use only that context for policy, masking, and audit.

If a runtime key is not bound to a user, the request is rejected.

### Internal identity context

The runtime service still needs an internal identity structure, but its source changes.

Recommended shape:

- `user_id`
- `role_ids`
- `org_node_id`

This object is internal-only and never accepted from untrusted client payloads.

### Audit model

Every runtime audit event should include:

- `api_key_id`
- `user_id`
- resolved roles
- `org_node_id`
- action metadata

This makes audit trails attributable to a single person and their directory placement.

## Authorization and Masking

### Resource policies

Resource policy subject picker supports:

- all users
- one user
- one role

### Field policies

Field policy subject picker supports:

- all users
- one user
- one role

### Masking policies

Masking subject picker supports:

- all users
- one user
- one role

### Organization and authorization

Organization nodes do not participate in allow or deny evaluation.

Organization is still visible in:

- user search
- user filtering
- audit context
- admin detail views

## Admin Console Information Architecture

### Navigation

Add:

- `Users`
- `Roles`

Retain:

- Overview
- Datasources
- Tags
- Access Policies
- Masking
- API Keys
- Audit Logs
- MCP Setup

There is no separate organization page.

### Users page

The users page becomes the enterprise directory workspace.

Layout:

- left pane: organization tree and search
- right pane: user list, filters, and user detail/editing

#### Left pane

- organization tree
- tree search
- expand/collapse
- per-node user counts

Organization maintenance actions live here:

- create root node
- create child node
- edit node
- delete empty node
- import users

#### Right pane

Top toolbar:

- current organization path
- create user
- import Excel
- connect importer
- role filter
- user search

User table columns:

- name
- organization path
- roles
- key status
- user status
- created time
- actions

User actions:

- view/edit
- reset key
- enable/disable

Detail drawer or side panel:

- user name
- organization selector
- multi-role selector
- key status
- reset key action
- one-time key reveal after create/reset

#### Key handling

- key value is hidden by default
- newly created or reset key is shown exactly once
- key is not persistently shown in tables

### Roles page

Independent admin page for role management.

Table columns:

- role name
- description
- assigned user count
- status
- created time

Actions:

- create role
- edit role
- disable role
- inspect assigned users

### API Keys page

This page narrows in scope.

It manages only system-level keys:

- admin keys
- internal keys

User runtime keys are not created here. They are created and reset from the users page.

### Policy pages

All policy forms must use searchable selectors instead of manual id input.

Subject types shown in UI:

- all
- user
- role

Subject selection:

- user picker for `user`
- role picker for `role`

No free-text `subject_id`.

## UI and UX Requirements

All admin UI changes must follow the previously established design direction and must explicitly reference the `web-design-engineer` guidance during implementation.

### UI rules

- Keep the current enterprise-console visual language rather than inventing a new theme.
- Favor dense, operational layouts over decorative marketing patterns.
- Preserve responsive behavior for wide and narrow desktop windows.
- Keep tree, table, drawer, and modal interactions coherent and stable.
- Avoid raw ids in visible workflows.
- Prefer search pickers, tree selectors, and direct actions.

### Production UI rules

- Remove development-only explanatory text.
- Show only operator-relevant information.
- Treat key generation, key reset, and imports as isolated modal or drawer workflows.

## Import Design

### Excel import

Only one template is supported.

Columns:

- `user_name`
- `org_path`
- `external_ref`
- `roles`

Rules:

- `org_path` uses a configurable organization delimiter
- default delimiter: `/`
- if `org_path` is empty, user is placed at the root level
- missing organization nodes are auto-created
- missing roles are auto-created
- `external_ref` is used for idempotent update

### Excel import UI

Entry point lives in the users page.

Open a modal with:

- click-to-upload
- drag-and-drop upload
- simple configuration section

Initial configuration:

- organization delimiter, default `/`

Flow:

1. choose file
2. adjust delimiter if needed
3. run preview validation
4. review summary
5. confirm import

Preview summary includes:

- users created
- users updated
- organization nodes created
- roles created
- invalid rows

### Third-party importers

Supported first-party connector categories:

- Feishu
- WeCom
- DingTalk

Architecture requirement:

- each platform is implemented as an importer connector
- no bidirectional sync
- no automatic continuous sync
- only administrator-triggered pull import

Each importer normalizes to the same ingestion model:

- user name
- organization path
- external ref
- roles if available and trusted

All platform imports reuse the same validation and persistence pipeline as Excel import.

## Key Lifecycle

### User creation

When an administrator creates a user:

1. create user
2. assign roles
3. bind organization node
4. generate one runtime API key automatically
5. display the plaintext key once

### User update

Updating name, roles, or organization does not rotate key automatically.

### Key reset

When an administrator resets a key:

1. old runtime key becomes invalid immediately
2. new runtime key is generated
3. plaintext is displayed once

### User disable

Disabling a user also disables that user's active runtime key.

## Direct Refactor Scope

This redesign replaces the current runtime identity contract rather than layering on top of it.

The implementation will directly refactor:

- `adg.app.dependencies`
- runtime tool schemas
- direct HTTP tool schemas
- runtime identity assembly
- policy subject validation
- admin console navigation and pages
- API key management responsibilities
- import workflows

The following subsystems should remain reusable with focused adaptation:

- datasource management
- resource catalog management
- tag management
- SQL Guard
- masking execution pipeline
- audit service

## Database and Alembic Strategy

This redesign does not preserve the current Alembic history.

Requirements:

- define the new database structure from scratch
- replace the existing migration lineage with a new baseline
- do not add compatibility migrations for the prior identity model

This project is not yet in production use, so a clean schema reset is the correct approach.

## Testing Strategy

### Backend

- API key authentication binds runtime requests to users
- runtime routes reject request-supplied identity fields
- one user can only hold one active runtime key
- user creation auto-generates runtime key
- key reset invalidates the old key
- disabling a user invalidates runtime access
- policy checks work for `all`, `user`, and `role`
- import preview and import execution behave deterministically
- importer connectors normalize into the shared ingestion pipeline

### Frontend

- users page renders organization tree plus user list workspace
- user create flow shows one-time generated key
- reset key flow shows one-time new key
- Excel import modal supports click upload and drag upload
- policy forms use searchable subject selectors
- API keys page excludes user runtime key creation

### Browser verification

- create user
- edit user
- reset user key
- disable user
- import Excel users
- create role
- create policy with user subject
- create policy with role subject
- verify MCP setup examples no longer mention caller-supplied identity fields

## Open decisions already settled in this design

- users do not log in to the console
- one user has one active runtime key
- users may have multiple roles
- organization is not an authorization subject
- Excel import uses one template only
- empty organization path maps users to root
- organization delimiter is configurable and defaults to `/`
- importer connectors are pull-only
- Alembic restarts from a new baseline
