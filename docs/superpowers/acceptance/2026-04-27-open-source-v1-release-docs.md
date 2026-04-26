# Acceptance Criteria: Open Source V1 Release Documentation and Governance

**Spec:** `docs/superpowers/specs/2026-04-27-open-source-v1-release-docs-design.md`
**Date:** 2026-04-27
**Status:** Draft

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | The repository root contains an English-first `README.md` that describes the current project rather than historical milestone narration. | Logic | The repository checkout is available locally. | `README.md` exists and includes sections covering project positioning, current capabilities, MVP boundaries, quickstart, verification commands, and documentation links. |
| AC-002 | The root `README.md` provides a direct visible link to the Chinese mirror. | Logic | `README.md` has been rewritten. | The top portion of `README.md` contains a link to `docs/zh-CN/README.md`. |
| AC-003 | A full Chinese mirror of the main README exists at `docs/zh-CN/README.md`. | Logic | The documentation pass has been applied. | `docs/zh-CN/README.md` exists and covers the same major topics as the English `README.md`. |
| AC-004 | The release docs separate current implementation from future roadmap content. | Logic | `README.md`, `docs/en/status.md`, and `docs/en/roadmap.md` exist. | Current implemented behavior is described in `README.md` and `docs/en/status.md`, while future work is described in `docs/en/roadmap.md` rather than being presented as already delivered. |
| AC-005 | The project has an English current-state document at `docs/en/status.md`. | Logic | The documentation pass has been applied. | `docs/en/status.md` exists and includes implemented capabilities, known limitations, and out-of-scope items. |
| AC-006 | The project has a Chinese mirror of the current-state document at `docs/zh-CN/status.md`. | Logic | `docs/en/status.md` exists. | `docs/zh-CN/status.md` exists and mirrors the major sections of `docs/en/status.md`. |
| AC-007 | The project has an English roadmap document at `docs/en/roadmap.md` with staged version planning. | Logic | The documentation pass has been applied. | `docs/en/roadmap.md` exists and includes versioned phases covering the current V1 baseline and later hardening/evolution stages. |
| AC-008 | The project has a Chinese mirror of the roadmap at `docs/zh-CN/roadmap.md`. | Logic | `docs/en/roadmap.md` exists. | `docs/zh-CN/roadmap.md` exists and mirrors the major roadmap stages from the English version. |
| AC-009 | The public docs treat `docs/superpowers/specs/2026-04-23-ai-data-access-gateway-v1-design.md` as historical context rather than current truth. | Logic | The release docs have been rewritten. | The outward-facing docs do not rely on that historical spec as the authority for current feature claims and instead describe the current repository state directly. |
| AC-010 | The repository root includes an Apache 2.0 `LICENSE` file matching the declared project license. | Logic | `pyproject.toml` declares Apache-2.0. | `LICENSE` exists at the repository root and contains Apache License 2.0 text. |
| AC-011 | The repository root includes an English `SECURITY.md` describing how to report vulnerabilities. | Logic | The governance file pass has been applied. | `SECURITY.md` exists and includes private vulnerability reporting guidance, scope expectations, and supported-version language suitable for an MVP project. |
| AC-012 | The repository root includes an English `CONTRIBUTING.md` with local setup and verification guidance. | Logic | The governance file pass has been applied. | `CONTRIBUTING.md` exists and includes setup prerequisites plus backend and frontend verification commands. |
| AC-013 | The repository root includes a recognizable open-source `CODE_OF_CONDUCT.md`. | Logic | The governance file pass has been applied. | `CODE_OF_CONDUCT.md` exists and contains a standard contributor conduct policy suitable for GitHub collaboration. |
| AC-014 | The repository root includes an `AGENTS.md` file for coding agents. | Logic | The governance file pass has been applied. | `AGENTS.md` exists and documents repository purpose, key directories, source-of-truth rules, verification commands, and bilingual-doc synchronization expectations. |
| AC-015 | Chinese mirror documents exist for the human-facing governance/process docs added in this pass. | Logic | Root governance docs have been added. | Chinese mirror files exist under `docs/zh-CN/` for the human-facing release/process docs and can be reached from the English-facing documentation path. |
| AC-016 | A GitHub CI workflow exists at `.github/workflows/ci.yml`. | Logic | The workflow pass has been applied. | `.github/workflows/ci.yml` exists and defines automated checks for backend tests, backend linting, backend typing, frontend tests, and frontend build on push and pull request events. |
| AC-017 | A GitHub security audit workflow exists at `.github/workflows/security-audit.yml`. | Logic | The workflow pass has been applied. | `.github/workflows/security-audit.yml` exists and defines scheduled and manually triggered dependency audit jobs for Python and frontend dependencies. |
| AC-018 | The CI workflow commands match the repository’s current toolchain. | Logic | `.github/workflows/ci.yml` exists. | The workflow uses commands consistent with the repository, specifically `uv run --extra dev pytest`, `uv run --extra dev ruff check .`, `uv run --extra dev mypy src tests`, `npm test`, and `npm run build`. |
| AC-019 | The security audit workflow does not silently suppress the current dependency audit reality. | Logic | `.github/workflows/security-audit.yml` and status/release docs exist. | The workflow runs real audit commands rather than placeholder no-op steps, and the docs do not claim a clean Python dependency audit if a known audit issue remains unresolved. |
| AC-020 | The rewritten docs accurately describe the current runtime/admin trust model and major MVP constraints. | Logic | The docs rewrite has been applied. | The docs state that the project currently uses API-key-based access, key-derived runtime identity, a single-service architecture, and does not present the admin console as a multi-operator enterprise IAM platform. |
