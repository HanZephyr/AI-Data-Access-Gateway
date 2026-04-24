# Milestone 3 MCP Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend MCP runtime tools, SQL Guard, and runtime policy checks for V1.

**Architecture:** Add focused control-plane models for tags and policies, transport-neutral runtime services, a conservative SQL Guard, and a small authenticated HTTP facade. Keep masking and full MCP protocol transport deferred to later milestones.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, sqlglot, pytest, ruff, mypy.

---

## File Structure

- `src/adg/control_plane/models/governance.py`: tag, resource tag, resource policy, and field policy models.
- `src/adg/policy/runtime.py`: identity context plus resource and field policy evaluation.
- `src/adg/sql_guard/guard.py`: AST-based conservative SQL Guard.
- `src/adg/connectors/base.py`: query connector protocol and result shape.
- `src/adg/connectors/relational.py`: read-only SQL execution for relational connectors.
- `src/adg/gateway_runtime/tools.py`: transport-neutral runtime tool service.
- `src/adg/mcp_api/tools.py`: authenticated HTTP tool facade.
- `src/adg/control_plane/migrations/versions/202604240001_initial_control_plane.py`: extend baseline tables.
- `tests/unit/policy/test_runtime_policy.py`: policy behavior.
- `tests/unit/sql_guard/test_guard.py`: SQL Guard behavior.
- `tests/unit/gateway_runtime/test_tools.py`: runtime tool service behavior.
- `tests/integration/test_mcp_tools_api.py`: HTTP facade behavior.
- `tests/integration/test_migrations.py`: migration table coverage.

## Tasks

### Task 1: Governance Tables

- [ ] Write failing model/migration tests asserting tag and policy tables exist.
- [ ] Add `governance.py` models and export them from `models/__init__.py`.
- [ ] Extend the baseline migration with `tags`, `resource_tags`, `resource_policies`, and `field_policies`.
- [ ] Run `pytest tests/integration/test_migrations.py -v` and commit.

### Task 2: Runtime Policy

- [ ] Write failing policy tests for default allow, deny override, allow when policies exist, tag policies, and field narrowing.
- [ ] Implement `IdentityContext`, `PolicyDecision`, and `RuntimePolicyService`.
- [ ] Run `pytest tests/unit/policy/test_runtime_policy.py -v` and commit.

### Task 3: SQL Guard

- [ ] Add `sqlglot` dependency.
- [ ] Write failing guard tests for allowed select, limit injection, mutation rejection, multiple statement rejection, and function whitelist rejection.
- [ ] Implement `SqlGuard`, `SqlGuardResult`, and resource/field extraction.
- [ ] Run `pytest tests/unit/sql_guard/test_guard.py -v` and commit.

### Task 4: Connector Query Execution

- [ ] Write failing connector/runtime tests that use a fake query connector result.
- [ ] Add query protocol shapes in `connectors/base.py`.
- [ ] Implement read-only relational `execute_query`.
- [ ] Run connector/runtime tests and commit.

### Task 5: Runtime Tools

- [ ] Write failing tests for `list_datasources`, `list_tags`, `list_resources`, `list_resources_by_tag`, `describe_resource`, `preview_resource`, and `execute_query`.
- [ ] Implement `GatewayRuntimeService` in `gateway_runtime/tools.py`.
- [ ] Record audit events for discovery, execution, SQL rejection, and permission rejection.
- [ ] Run `pytest tests/unit/gateway_runtime/test_tools.py -v` and commit.

### Task 6: MCP HTTP Facade

- [ ] Write failing API tests for authenticated non-admin runtime access and unknown tools.
- [ ] Implement `src/adg/mcp_api/tools.py` and include the router in `app/main.py`.
- [ ] Run `pytest tests/integration/test_mcp_tools_api.py -v` and commit.

### Task 7: Final Verification and Memory

- [ ] Run `pytest`, `ruff check .`, and `mypy src tests`.
- [ ] Update README and repository memory for Milestone 3.
- [ ] Commit memory/docs updates.
- [ ] Merge the branch back to `main` locally, then continue to Milestone 4.
