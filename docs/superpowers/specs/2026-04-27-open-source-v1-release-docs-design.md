# Open Source V1 Release Documentation and Governance Design

**Date:** 2026-04-27
**Status:** Approved

---

## Scope

This design defines the documentation, governance, and GitHub automation work required to publish the current AI Data Access Gateway repository as a professional V1 MVP open-source project.

The goal is not to add new runtime features. The goal is to make the current repository understandable, legally publishable, contributor-friendly, and explicit about what is already implemented versus what remains future work.

This design treats the current repository code, tests, configuration, and runnable paths as the source of truth. Earlier design artifacts remain useful historical references but must not be copied forward when they no longer match the implemented repository state.

## Goals

- Publish a professional English-first open-source project surface for GitHub.
- Provide a complete Chinese mirror for all user-facing release documentation.
- Rewrite the main project description so it reflects the current repository state rather than historical plans.
- Separate current capability, known limitations, and future roadmap into distinct documents.
- Add the minimum governance files expected for a serious open-source MVP release.
- Add baseline GitHub CI and dependency audit workflows appropriate for the current stack.
- Create a repository-level `AGENTS.md` file so coding agents can operate safely and consistently in this codebase.

## Non-Goals

- No new gateway runtime, policy, masking, connector, or admin-console features.
- No architectural refactor of the backend or frontend.
- No release automation, package publishing automation, or semantic-versioning pipeline in this pass.
- No new issue templates, PR templates, release-draft workflows, or advanced community-management features in this pass.
- No attempt to claim enterprise-grade security posture beyond the current MVP boundaries.

## Source-of-Truth Policy

The published documentation must follow this evidence hierarchy:

1. Current repository implementation under `src/`, `web/`, `examples/`, Docker files, and migrations.
2. Current automated verification results and supported development commands.
3. Existing internal repository memory and accepted design docs, but only when they still match current code.
4. Historical design documents as background only.

The document `docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md` must be treated as a historical internal design artifact, not as an externally published statement of current fact. Any capability in that document that has already been delivered should be rewritten as current implementation. Any capability that remains future work should be moved into roadmap documents rather than described as present behavior.

## Documentation Information Model

The release documentation must clearly separate three kinds of information:

### 1. Current Implementation

This section describes what the repository actually provides today:

- backend surfaces
- runtime tools
- governance model
- masking and decrypt behavior
- admin console capabilities
- demo and bootstrap flow
- packaging and verification commands

Claims in this section must be supportable by the current repository state.

### 2. MVP Boundaries and Known Limitations

This section describes what the project intentionally does not provide in V1 and what users should not assume:

- not a BI product
- not a multi-operator admin platform
- not an enterprise IAM or SSO system
- not row-level policy enforcement
- not a full enterprise deployment platform
- not a zero-trust production-ready managed service

This section must reduce over-claiming and help users decide whether the project fits their use case.

### 3. Roadmap and Versioned Evolution

This section captures future direction in structured version increments rather than mixing future ideas into the README body. It should explain how the project can evolve from MVP hardening into broader enterprise-oriented capabilities.

## Documentation Structure

The repository must use an English-first landing experience with complete Chinese mirrors:

- `README.md`
  - default English landing page in the repository root
  - prominent direct link to the Chinese mirror
- `docs/zh-CN/README.md`
  - full Chinese mirror of the main README
- `docs/en/status.md`
  - English current-state and limitation document
- `docs/zh-CN/status.md`
  - Chinese mirror of the current-state and limitation document
- `docs/en/roadmap.md`
  - English roadmap and staged version plan
- `docs/zh-CN/roadmap.md`
  - Chinese mirror of the roadmap

The English and Chinese versions must be parallel in substance. The Chinese documents are not summaries; they are mirror pages.

## Root README Design

The root `README.md` must become the standard open-source entry point. It should include:

- project summary and positioning
- English/Chinese doc switch links near the top
- why the project exists
- key V1 capabilities
- architecture summary
- current MVP boundaries
- repository layout summary
- local quickstart
- Docker Compose quickstart
- verification commands
- documentation index
- roadmap link
- contribution and security links
- license reference

The README must avoid:

- milestone-by-milestone historical narration as the primary structure
- statements that imply unfinished roadmap items are already delivered
- vague claims such as "enterprise-grade" without qualification

## Status Document Design

The status document must make the repository state explicit and reviewable. It should include:

- current release positioning: V1 MVP
- implemented backend capabilities
- implemented frontend/admin-console capabilities
- supported development and packaging flows
- known limitations
- out-of-scope items
- recommended near-term hardening priorities

It must be readable by both evaluators and contributors who want to know what still needs work.

## Roadmap Design

The roadmap must convert historical future ideas into a clean staged plan. Recommended structure:

- `V1.0`
  - current MVP baseline
- `V1.1`
  - documentation and open-source hardening
  - CI/audit stabilization
  - low-risk product hardening
- `V1.2`
  - operational hardening and deployment improvements
  - better observability and security controls
- `V2.0`
  - enterprise foundation capabilities such as stronger admin auth, better production deployment posture, and policy expansion
- `V3.0`
  - ecosystem and extensibility goals such as broader datasource support and richer MCP/runtime integration

The roadmap should explicitly distinguish:

- likely next work
- medium-term architectural direction
- longer-term aspirational items

## Governance Files

The repository must add the following root files:

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `AGENTS.md`

### LICENSE

Because `pyproject.toml` already declares Apache-2.0, the repository must include a matching Apache 2.0 license file at the root.

### SECURITY.md

The security policy should define:

- supported versions in practical MVP terms
- how to report vulnerabilities privately
- what not to report through public issues
- response expectations framed conservatively

It should not promise enterprise incident-response rigor that the project cannot yet support.

### CONTRIBUTING.md

The contribution guide should define:

- development prerequisites
- local setup
- backend and frontend verification commands
- expectations for tests and docs updates
- preferred style for focused pull requests

### CODE_OF_CONDUCT.md

Use a standard and recognizable open-source code of conduct suitable for public GitHub collaboration.

### AGENTS.md

`AGENTS.md` must guide coding agents operating in the repository. It should include:

- repository purpose
- source-of-truth rule: implementation over old design docs
- key directories and responsibilities
- setup and verification commands
- constraints on editing generated or unrelated files
- requirement to keep English and Chinese docs in sync when release docs are changed
- guidance to update status/roadmap docs when scope changes materially

The file should be useful to Codex and also intelligible to other coding agents.

## Chinese Mirror Policy

Chinese mirrors should exist for all human-facing release docs added in this pass:

- Chinese README mirror
- Chinese status document
- Chinese roadmap document
- Chinese mirrors for governance/process docs under `docs/zh-CN/`

The root governance files may remain English-first because GitHub convention expects root policy files there, but each should link to the Chinese mirror when useful.

The mirror policy is substance parity, not necessarily identical sentence structure.

## GitHub Workflow Design

### CI Workflow

Add `.github/workflows/ci.yml` with triggers on push and pull request.

It should run:

- backend tests with `uv run --extra dev pytest`
- backend lint with `uv run --extra dev ruff check .`
- backend typing with `uv run --extra dev mypy src tests`
- frontend tests with `npm test`
- frontend production build with `npm run build`

The workflow should use a practical matrix only if necessary. Simplicity is preferred for V1.

### Security Audit Workflow

Add `.github/workflows/security-audit.yml` with:

- scheduled execution
- manual dispatch

It should run:

- `uv tool run pip-audit`
- `npm audit --omit=dev --registry=https://registry.npmjs.org`

Because the current environment already reports `pip 26.0.1 / CVE-2026-3219`, the workflow and docs must avoid pretending the repo is clean when it is not. The preferred design is:

- keep the audit workflow real and failing when real vulnerabilities exist
- document the known current audit issue in release documentation or the status document if it remains unresolved in this pass

This preserves trust in the automation instead of silently weakening checks.

## Content Accuracy Rules

The rewritten documentation must align with the current implemented repository, including:

- API-key based admin and runtime access
- key-derived runtime identity model
- single-service FastAPI architecture
- Streamable HTTP MCP mounting and MCP-style HTTP tool route
- masking and runtime decrypt support
- admin console behavior that keeps admin API keys in browser memory only
- encrypted persisted datasource secrets
- current Docker Compose shape
- current tests and verification commands

It must also explicitly note current gaps where appropriate, such as:

- no separate admin login system or SSO
- no enterprise operator RBAC for the admin console
- no row-level data access control
- no advanced production controls such as rate limiting or hardened TLS termination in the repository itself

## Writing Style

All outward-facing docs should be:

- explicit
- professional
- conservative in claims
- easy to scan
- useful to evaluators, users, and contributors

Avoid:

- inflated language
- ambiguous roadmap promises
- internal milestone jargon without explanation
- mixing historical chronology into user-facing onboarding

## Verification Strategy

This documentation-and-governance pass should preserve current verification quality. Before claiming completion, run:

- `uv run --extra dev pytest`
- `uv run --extra dev ruff check .`
- `uv run --extra dev mypy src tests`
- `cd web && npm test`
- `cd web && npm run build`

For workflow correctness, the YAML files should also be read back and sanity-checked after writing.

## Deliverables

This design is complete when the repository contains:

- rewritten English root README
- Chinese README mirror
- English and Chinese status docs
- English and Chinese roadmap docs
- root open-source governance files
- Chinese mirrors for human-facing governance docs
- `AGENTS.md`
- CI workflow
- security audit workflow

And when the content consistently reflects the current codebase rather than outdated design assumptions.
