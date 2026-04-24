# Milestone 6 Documentation, Demo, and Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete V1 with docs, demo seed, MCP client examples, Docker demo files, and final verification.

**Architecture:** Keep demo assets in `examples/` and root Docker files; do not change runtime behavior unless tests expose a gap.

**Tech Stack:** Python, FastAPI, SQLite, Docker Compose, React/Vite, pytest.

---

## Tasks

### Task 1: Demo Seed and Tests

- [ ] Write failing test for demo seed data.
- [ ] Implement `examples/seed_demo.py`.
- [ ] Run the focused test and commit.

### Task 2: Docs and Examples

- [ ] Add MCP HTTP client example.
- [ ] Expand README quickstart.
- [ ] Add Dockerfile and compose file.
- [ ] Run docs-oriented checks and commit.

### Task 3: Final Verification

- [ ] Run backend tests, ruff, mypy, and web build.
- [ ] Start backend and web console with demo seed.
- [ ] Use browser tooling to click through the console and verify no console errors.
- [ ] Merge to `main` and do final V1 verification on `main`.
