# Open Source V1 Release Documentation and Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the current AI Data Access Gateway repository as a professional English-first, Chinese-mirrored V1 MVP open-source project with accurate docs, governance files, and baseline GitHub automation.

**Architecture:** Treat the current repository implementation and tests as the source of truth, then build a clean outward-facing documentation surface around that truth. Split the work into four bounded areas: root governance files, English release docs, Chinese mirrors, and GitHub workflows, then finish with full repository verification so the release surface matches the actual codebase.

**Tech Stack:** Markdown, Apache 2.0 license text, GitHub Actions YAML, Python `uv` toolchain, Node/Vite/Vitest workflow, PowerShell verification commands

---

### Task 1: Establish The Root Open-Source Governance Surface

**Files:**
- Create: `LICENSE`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-04-27-open-source-v1-release-docs-design.md`
- Modify: `docs/superpowers/acceptance/2026-04-27-open-source-v1-release-docs.md`

- [ ] **Step 1: Confirm the repository currently lacks the governance files**

Run:

```powershell
@('LICENSE','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','AGENTS.md') | ForEach-Object {
  if (Test-Path $_) { "PRESENT $_" } else { "MISSING $_" }
}
```

Expected: every listed file prints `MISSING ...` before this task is implemented.

- [ ] **Step 2: Add the Apache 2.0 root license file**

Write `LICENSE` with the standard Apache License 2.0 body:

```text
Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.
...
END OF TERMS AND CONDITIONS
```

The final file must be the complete standard Apache 2.0 license text, not an abbreviated excerpt.

- [ ] **Step 3: Add the root security policy**

Write `SECURITY.md` with this structure and substance:

```markdown
# Security Policy

## Supported Versions

The project is currently in an MVP stage. Security fixes are expected to land on the latest mainline version first. Older snapshots, forks, and unmaintained branches should not be assumed to receive backports.

## Reporting A Vulnerability

Do not open public GitHub issues for suspected vulnerabilities.

Please report security issues privately to the project maintainers through the repository contact channel or a dedicated security email if one is later configured.

When reporting, include:

- affected version or commit
- deployment context
- reproduction steps
- expected impact
- any suggested mitigation

The maintainers will review the report, confirm whether it is in scope, and coordinate disclosure conservatively based on available maintainer capacity.

## Scope Notes

This repository is an open-source MVP. Reports are welcome for:

- authentication and authorization bypass
- secret disclosure
- masking or decrypt control bypass
- SQL guard bypass that enables forbidden execution paths
- admin or runtime API exposure flaws

Out-of-scope examples may include:

- vulnerabilities only present in unsupported forks
- reports that require local privileged shell access without a gateway flaw
- purely theoretical issues without a demonstrable repository impact
```

- [ ] **Step 4: Add the root contribution guide**

Write `CONTRIBUTING.md` with this structure:

```markdown
# Contributing

## Scope

This project is currently released as a V1 MVP. Contributions should prefer focused, reviewable changes over broad speculative refactors.

## Prerequisites

- Python 3.12+
- Node.js 20+
- `uv`
- `npm`

## Local Setup

### Backend

```powershell
uv sync --extra dev --extra all
```

### Frontend

```powershell
Set-Location web
npm ci
Set-Location ..
```

## Verification

### Backend

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
```

### Frontend

```powershell
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
```

## Pull Request Expectations

- keep changes focused
- update tests when behavior changes
- update English and Chinese docs together when release-facing docs change
- do not claim capabilities that the repository does not yet implement
```

- [ ] **Step 5: Add the root code of conduct**

Write `CODE_OF_CONDUCT.md` using a standard Contributor Covenant-style policy with sections for:

```markdown
# Code Of Conduct

## Our Pledge
## Our Standards
## Enforcement Responsibilities
## Scope
## Enforcement
## Attribution
```

The completed file should be a full, recognizable open-source conduct policy suitable for public GitHub collaboration.

- [ ] **Step 6: Add the root `AGENTS.md` file**

Write `AGENTS.md` with this structure and repository-specific guidance:

```markdown
# AGENTS

## Repository Purpose

AI Data Access Gateway is a secure data access gateway MVP for AI agents. It exposes governed metadata discovery and read-only runtime data access with authorization, SQL safety checks, masking, runtime decrypt controls, and audit logging.

## Source Of Truth

- Current code, tests, and runnable configuration are the source of truth.
- Historical design docs under `docs/superpowers/specs/` are useful context but must not override the implemented repository state.
- If a historical design doc conflicts with current code, follow current code and update outward-facing docs accordingly.

## Important Directories

- `src/adg/`: backend application code
- `tests/`: backend unit and integration coverage
- `web/`: React + Vite admin console
- `examples/`: demo seed and example client flows
- `docs/en/`: English release-facing project docs
- `docs/zh-CN/`: Chinese mirror docs
- `docs/superpowers/`: internal planning, spec, and repository memory artifacts

## Working Rules

- Keep release-facing English and Chinese docs in sync.
- Do not describe roadmap items as current features.
- Prefer minimal, bounded edits over broad unrelated cleanup.
- Do not remove or overwrite internal planning artifacts unless explicitly asked.

## Verification Commands

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
```
```

- [ ] **Step 7: Mark the approved design and acceptance docs as approved**

Update the headers in these files:

```markdown
docs/superpowers/specs/2026-04-27-open-source-v1-release-docs-design.md
**Status:** Approved

docs/superpowers/acceptance/2026-04-27-open-source-v1-release-docs.md
**Status:** Approved
```

- [ ] **Step 8: Verify the governance files exist and are populated**

Run:

```powershell
@('LICENSE','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','AGENTS.md') | ForEach-Object {
  Get-Item $_ | Select-Object Name,Length
}
```

Expected: all five files exist and each file has a non-trivial length greater than zero.

- [ ] **Step 9: Commit the governance surface**

Run:

```powershell
git add LICENSE SECURITY.md CONTRIBUTING.md CODE_OF_CONDUCT.md AGENTS.md docs/superpowers/specs/2026-04-27-open-source-v1-release-docs-design.md docs/superpowers/acceptance/2026-04-27-open-source-v1-release-docs.md
git commit -m "docs: add release governance surface"
```

Expected: one commit is created containing the new governance files and approved status updates.

### Task 2: Rewrite The English Release-Facing Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/en/status.md`
- Create: `docs/en/roadmap.md`

- [ ] **Step 1: Re-read the current source-of-truth material before rewriting docs**

Run:

```powershell
Get-Content README.md
Get-Content docs/superpowers/memory/index.md
Get-Content docs/superpowers/specs/2026-04-26-security-hardening-runtime-admin-design.md
```

Expected: the current root README is historical/minimal, while repository memory and approved designs expose the current implementation boundaries to carry into the new docs.

- [ ] **Step 2: Rewrite the root `README.md` as the English-first project landing page**

Replace `README.md` with a structure like this:

```markdown
# AI Data Access Gateway

[中文文档 / Chinese Mirror](docs/zh-CN/README.md)

AI Data Access Gateway is an open-source secure data access gateway for AI agents. It sits between AI agents and real datasources and exposes governed metadata discovery and read-only runtime access with authorization, SQL safety checks, masking, runtime decrypt controls, and audit logging.

## Project Status

This repository is currently published as a V1 MVP. It is suitable for local evaluation, guided demos, and iterative open-source development. It should not be described as an enterprise-ready control plane or production-hardened zero-trust platform in its current form.

## What It Does Today

- FastAPI backend with admin, runtime, and MCP-facing surfaces
- API-key-based admin access and runtime access
- Key-derived runtime identity bound to directory users and roles
- Datasource registration and metadata scanning for relational datasources
- Resource and field policy enforcement
- Conservative SQL guard for read-only execution
- Masking policies including reversible masking with runtime decrypt control
- Audit event persistence
- React + Vite admin console
- Demo seed data and Docker Compose packaging

## MVP Boundaries

- no separate admin login system, SSO, or MFA
- no row-level policy enforcement
- no multi-operator admin RBAC model
- no built-in TLS termination in the repository
- no claim of enterprise-grade deployment hardening

## Architecture

...

## Repository Layout

...

## Quickstart

### Backend

```powershell
uv sync --extra dev --extra all
uv run --extra dev python examples/seed_demo.py --database-url sqlite:///./data/adg-control-plane.db
$env:ADG_CONTROL_PLANE_DATABASE_URL=\"sqlite:///./data/adg-control-plane.db\"
$env:ADG_SECRET_KEY=\"<generate-a-long-random-secret>\"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY=\"<generate-a-second-long-random-secret>\"
uv run --extra dev uvicorn adg.app.main:create_app --factory --reload
```

### Frontend

```powershell
Set-Location web
npm ci
npm run dev
```

### Docker Compose

```powershell
$env:ADG_SECRET_KEY=\"<generate-a-long-random-secret>\"
$env:ADG_CREDENTIAL_ENCRYPTION_KEY=\"<generate-a-second-long-random-secret>\"
docker compose up --build
docker exec -it ai-data-access-gateway-backend-1 init-admin
```

## Verification

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
```

## Documentation

- [Project Status](docs/en/status.md)
- [Roadmap](docs/en/roadmap.md)
- [Chinese README](docs/zh-CN/README.md)
- [Chinese Status](docs/zh-CN/status.md)
- [Chinese Roadmap](docs/zh-CN/roadmap.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

Licensed under Apache 2.0. See [LICENSE](LICENSE).
```

The final README should be complete prose, not a sparse outline.

- [ ] **Step 3: Write the English status document**

Create `docs/en/status.md` with this structure:

```markdown
# Project Status

## Release Positioning

AI Data Access Gateway is currently released as a V1 MVP.

## Implemented Today

### Backend
- ...

### Runtime and governance
- ...

### Admin console
- ...

### Packaging and demo flow
- ...

## Known Limitations

- ...

## Explicitly Out Of Scope For The Current MVP

- ...

## Near-Term Hardening Priorities

- ...
```

The concrete bullets must reflect the current repository implementation rather than historic milestone labels.

- [ ] **Step 4: Write the English roadmap document**

Create `docs/en/roadmap.md` with this structure:

```markdown
# Roadmap

## Principles

- current code is the source of truth
- roadmap items are not present capabilities
- version names indicate planning direction, not guaranteed dates

## V1.0: Current MVP Baseline

- summarize what is already in the repository

## V1.1: Open-Source And Documentation Hardening

- release documentation polish
- governance files
- CI and dependency audit workflows

## V1.2: Operational Hardening

- admin auth hardening
- deployment and observability improvements
- safer production posture

## V2.0: Enterprise Foundation

- stronger admin authentication model
- richer policy controls
- operational controls expected by larger teams

## V3.0: Ecosystem Expansion

- broader datasource support
- better extensibility
- richer runtime and MCP ecosystem integration
```

The final content should describe realistic staged evolution and note that enterprise-grade features remain future work.

- [ ] **Step 5: Verify the English docs contain the required navigation and boundaries**

Run:

```powershell
Select-String -Path README.md -Pattern 'Chinese Mirror','Project Status','What It Does Today','MVP Boundaries','Verification','docs/en/status.md','docs/en/roadmap.md'
Select-String -Path docs/en/status.md -Pattern 'Known Limitations','Out Of Scope','Near-Term Hardening Priorities'
Select-String -Path docs/en/roadmap.md -Pattern 'V1.0','V1.1','V1.2','V2.0','V3.0'
```

Expected: each command finds the required headings or links.

- [ ] **Step 6: Commit the English release docs**

Run:

```powershell
git add README.md docs/en/status.md docs/en/roadmap.md
git commit -m "docs: rewrite English release documentation"
```

Expected: one commit is created for the English release-facing docs.

### Task 3: Create The Chinese Mirror Documentation Set

**Files:**
- Create: `docs/zh-CN/README.md`
- Create: `docs/zh-CN/status.md`
- Create: `docs/zh-CN/roadmap.md`
- Create: `docs/zh-CN/security.md`
- Create: `docs/zh-CN/contributing.md`
- Create: `docs/zh-CN/code-of-conduct.md`

- [ ] **Step 1: Create the Chinese README mirror**

Write `docs/zh-CN/README.md` as a full Chinese mirror of the root README with this structure:

```markdown
# AI Data Access Gateway

[English README](../../README.md)

AI Data Access Gateway 是一个面向 AI Agent 的开源安全数据访问网关。

## 项目状态

...

## 当前已实现

...

## MVP 边界

...

## 架构概览

...

## 快速开始

...

## 验证命令

...

## 文档导航

- [项目现状](status.md)
- [发展路线图](roadmap.md)
- [English README](../../README.md)
```

- [ ] **Step 2: Create the Chinese status mirror**

Write `docs/zh-CN/status.md` as a full Chinese mirror of the English status doc:

```markdown
# 项目现状

## 发布定位
## 当前已实现能力
## 已知限制
## 当前 MVP 明确不包含的内容
## 近期加固优先项
```

- [ ] **Step 3: Create the Chinese roadmap mirror**

Write `docs/zh-CN/roadmap.md` as a full Chinese mirror of the English roadmap:

```markdown
# 路线图

## 规划原则
## V1.0：当前 MVP 基线
## V1.1：开源与文档加固
## V1.2：运行与安全加固
## V2.0：企业能力基础
## V3.0：生态扩展
```

- [ ] **Step 4: Create Chinese mirrors for the human-facing governance docs**

Write:

```markdown
docs/zh-CN/security.md
docs/zh-CN/contributing.md
docs/zh-CN/code-of-conduct.md
```

Each file should be a Chinese mirror of its English root counterpart and include a link back to the English original near the top.

- [ ] **Step 5: Add Chinese cross-links from the root governance docs where useful**

Add a short line near the top of each of these files:

```markdown
SECURITY.md -> Chinese mirror: `docs/zh-CN/security.md`
CONTRIBUTING.md -> Chinese mirror: `docs/zh-CN/contributing.md`
CODE_OF_CONDUCT.md -> Chinese mirror: `docs/zh-CN/code-of-conduct.md`
```

- [ ] **Step 6: Verify mirror file existence and navigation**

Run:

```powershell
@(
  'docs/zh-CN/README.md',
  'docs/zh-CN/status.md',
  'docs/zh-CN/roadmap.md',
  'docs/zh-CN/security.md',
  'docs/zh-CN/contributing.md',
  'docs/zh-CN/code-of-conduct.md'
) | ForEach-Object { Get-Item $_ | Select-Object Name,Length }
```

Expected: all six files exist and each has non-zero content length.

- [ ] **Step 7: Commit the Chinese mirror docs**

Run:

```powershell
git add docs/zh-CN README.md SECURITY.md CONTRIBUTING.md CODE_OF_CONDUCT.md
git commit -m "docs: add Chinese mirror documentation"
```

Expected: one commit is created for the Chinese mirror set and cross-links.

### Task 4: Add Baseline GitHub CI And Security Audit Workflows

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/security-audit.yml`

- [ ] **Step 1: Create the CI workflow**

Write `.github/workflows/ci.yml` with jobs that cover the repository’s current stack:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Sync backend dependencies
        run: uv sync --extra dev --extra all
      - name: Pytest
        run: uv run --extra dev pytest
      - name: Ruff
        run: uv run --extra dev ruff check .
      - name: Mypy
        run: uv run --extra dev mypy src tests

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/package-lock.json
      - name: Install frontend dependencies
        working-directory: web
        run: npm ci
      - name: Frontend tests
        working-directory: web
        run: npm test
      - name: Frontend build
        working-directory: web
        run: npm run build
```

- [ ] **Step 2: Create the security audit workflow**

Write `.github/workflows/security-audit.yml` with scheduled and manual triggers:

```yaml
name: Security Audit

on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * 1'

jobs:
  backend-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Run pip-audit
        run: uv tool run pip-audit

  frontend-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/package-lock.json
      - name: Install frontend dependencies
        working-directory: web
        run: npm ci
      - name: Run production dependency audit
        working-directory: web
        run: npm audit --omit=dev --registry=https://registry.npmjs.org
```

- [ ] **Step 3: Document the current Python audit reality in the status docs if the audit still fails**

If `uv tool run pip-audit` still reports the current `pip` vulnerability at implementation time, add a short explicit note to:

```markdown
docs/en/status.md
docs/zh-CN/status.md
```

The note should say that frontend production audit is currently clean, while Python dependency auditing may still report a tooling-chain issue that remains to be resolved.

- [ ] **Step 4: Verify the workflow files contain the required commands and triggers**

Run:

```powershell
Select-String -Path .github/workflows/ci.yml -Pattern 'uv run --extra dev pytest','uv run --extra dev ruff check .','uv run --extra dev mypy src tests','npm test','npm run build','pull_request'
Select-String -Path .github/workflows/security-audit.yml -Pattern 'workflow_dispatch','schedule','uv tool run pip-audit','npm audit --omit=dev --registry=https://registry.npmjs.org'
```

Expected: the required commands and triggers are present in the two workflow files.

- [ ] **Step 5: Commit the workflow automation**

Run:

```powershell
git add .github/workflows/ci.yml .github/workflows/security-audit.yml docs/en/status.md docs/zh-CN/status.md
git commit -m "ci: add release verification workflows"
```

Expected: one commit is created for the workflow automation and any related status doc note.

### Task 5: Run Full Repository Verification And Final Sanity Checks

**Files:**
- Verify only: `README.md`, `docs/en/*.md`, `docs/zh-CN/*.md`, root governance docs, `.github/workflows/*.yml`

- [ ] **Step 1: Run the backend verification suite**

Run:

```powershell
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
```

Expected: all tests pass, Ruff reports no errors, and mypy reports no issues.

- [ ] **Step 2: Run the frontend verification suite**

Run:

```powershell
Set-Location web
npm test
npm run build
npm run audit:prod
Set-Location ..
```

Expected: frontend tests pass, the production build succeeds, and the production dependency audit completes without frontend vulnerabilities.

- [ ] **Step 3: Run the Python dependency audit**

Run:

```powershell
uv tool run pip-audit
```

Expected: either the command passes cleanly or, if it still fails on the known tooling-chain issue, the final docs accurately disclose that status rather than claiming a clean Python audit.

- [ ] **Step 4: Sanity-check the bilingual documentation surface**

Run:

```powershell
Select-String -Path README.md -Pattern 'docs/zh-CN/README.md','docs/en/status.md','docs/en/roadmap.md','SECURITY.md','CONTRIBUTING.md'
Select-String -Path docs/zh-CN/README.md -Pattern '../../README.md','status.md','roadmap.md'
```

Expected: the English and Chinese landing pages both contain the expected navigation links.

- [ ] **Step 5: Review the working tree and commit the final release-docs pass**

Run:

```powershell
git status --short
git add README.md docs/en docs/zh-CN LICENSE SECURITY.md CONTRIBUTING.md CODE_OF_CONDUCT.md AGENTS.md .github/workflows
git commit -m "docs: publish open source V1 release surface"
```

Expected: the working tree shows only the intended documentation/governance/workflow changes and the final commit succeeds.
