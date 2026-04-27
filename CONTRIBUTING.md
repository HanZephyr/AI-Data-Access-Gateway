# Contributing

Chinese mirror: [简体中文](docs/zh-CN/contributing.md)

## Scope

AI Data Access Gateway is currently released as a V1 MVP. Contributions should prefer focused, reviewable changes over broad speculative refactors. Changes that materially affect release-facing behavior or documentation should stay explicit about current implementation boundaries.

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

Run the relevant verification commands before opening a pull request.

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

- keep changes focused and reviewable
- update tests when behavior changes
- update English and Chinese docs together when release-facing docs change
- do not claim capabilities that the repository does not yet implement
- preserve unrelated user or teammate changes in the working tree
- explain any security, schema, or API-surface impact in the pull request description

## Development Notes

- Treat current code, tests, and runnable configuration as the source of truth.
- Historical design artifacts may provide context, but they should not override implemented behavior.
- If you need to make a larger change, split it into sequenced pull requests when practical so review and rollback remain straightforward.
