# Milestone 4 Masking and Decryption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add masking policies, reversible decrypt contexts, runtime masking, and the internal decrypt API.

**Architecture:** Extend the control-plane baseline with masking/decrypt models, add a dedicated masking service, integrate it into `GatewayRuntimeService` after connector execution, and expose `/internal/decrypt` through FastAPI.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, cryptography Fernet, pytest, ruff, mypy.

---

## Tasks

### Task 1: Tables and Models

- [ ] Write failing migration tests for `masking_policies` and `decrypt_contexts`.
- [ ] Add masking/decrypt models and export them.
- [ ] Extend the baseline migration.
- [ ] Run migration tests and commit.

### Task 2: Masking Service

- [ ] Add failing tests for fixed, partial, hash, reversible, and expired decrypt behavior.
- [ ] Add `cryptography` dependency.
- [ ] Implement `MaskingService` and helper result shapes.
- [ ] Run masking tests and commit.

### Task 3: Runtime Integration

- [ ] Add failing runtime tests proving masked values and metadata are returned from `execute_query`.
- [ ] Apply masking after connector execution and include masking metadata in query response and audit metadata.
- [ ] Run runtime tests and commit.

### Task 4: Internal Decrypt API

- [ ] Add failing API tests for successful decrypt and expired-context rejection.
- [ ] Implement `src/adg/internal_api/decrypt.py` and include the router.
- [ ] Run API tests and commit.

### Task 5: Final Verification and Memory

- [ ] Run `uv run --extra dev pytest`, `uv run --extra dev ruff check .`, and `uv run --extra dev mypy src tests`.
- [ ] Update README and repository memory.
- [ ] Merge the branch back to `main` locally, then continue to Milestone 5.
