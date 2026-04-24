# Milestone 5 Web Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the V1 management APIs and React/Ant Design web console.

**Architecture:** Keep backend admin APIs in focused routers and build `web/` as a separate Vite app that consumes those APIs with a small typed client.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, Vite, Ant Design, pytest, ruff, mypy, npm build.

---

## Tasks

### Task 1: Admin API Coverage

- [ ] Write failing integration tests for resources, tags, policies, masking policies, API keys, audit query, and MCP setup.
- [ ] Implement focused admin routers and include them in `create_app`.
- [ ] Run backend tests and commit.

### Task 2: Web Console Scaffold

- [ ] Add `web/package.json`, Vite config, TypeScript config, and source files.
- [ ] Build a dense Ant Design console with overview, datasources, resources, tags, policies, masking, API keys, audit, and MCP setup pages.
- [ ] Run `npm install` and `npm run build`; commit package lock and source.

### Task 3: Browser Verification

- [ ] Start the FastAPI server and Vite dev server.
- [ ] Use browser tooling to click through navigation and confirm no console errors.
- [ ] Fix any UI or runtime issues.

### Task 4: Memory and Merge

- [ ] Run full backend and frontend verification.
- [ ] Update README and repository memory.
- [ ] Merge to `main` and continue to Milestone 6.
