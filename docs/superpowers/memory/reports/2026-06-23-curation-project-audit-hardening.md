## Summary
- Result: updated
- Source spec: user-provided repository memory update request for `codex/project-audit-hardening`
- Source context: `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md`, `docs/superpowers/memory/modules/milestone-5-web-console.md`, current runtime/proxy/lockfile implementation
- Source design: `none`
- Formal commits: `a90fa7c`, `cb7c2ef`, `7587e07`, `9b0b509`
- Created docs: 1
- Updated docs: 2
- Deferred docs: 0

## Durable updates made
- Module cards: updated `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md` with current runtime entrypoints: FastMCP Streamable HTTP `/mcp` and simpler `POST /api/tools/{tool_name}` HTTP tools.
- Module cards: updated `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md` with the runtime identity invariant: runtime API keys bind the user identity, and tool payloads must not supply trusted `user_id`, `roles`, or `groups`.
- Module cards: updated `docs/superpowers/memory/modules/milestone-3-mcp-runtime.md` with the obsolete historical `/mcp/tools/{tool_name}` pitfall and the need to proxy `/mcp` plus `/api/tools/`.
- Module cards: updated `docs/superpowers/memory/modules/milestone-5-web-console.md` with the production Nginx and local Vite dev server requirement to proxy `/api/tools/` to the backend.
- Module cards: updated `docs/superpowers/memory/modules/milestone-5-web-console.md` with the `web/package-lock.json` registry invariant: tarball `resolved` URLs stay canonical `https://registry.npmjs.org/` while `NPM_REGISTRY_URL` remains the install-time override.
- Contracts: no standalone contract document created; the endpoint and lockfile rules fit the existing runtime and web console module cards.
- Decisions: no separate decision document created.
- Runbooks: no reusable operational sequence was introduced.
- Lessons: captured recurring pitfalls in the existing module cards instead of adding a duplicate lesson document.

## Not promoted
- The raw audit mismatch write-up from `cb7c2ef` was not copied into canonical memory; only its durable endpoint/proxy mismatch lessons were retained.
- Formal commits `89d64cd` and `11d1d2d` were not promoted in this pass because this update scope focused on runtime entrypoints, web proxying, and lockfile registry behavior rather than field-policy batching or CI audit constraints.
- Local command output and transient worktree warnings were left out of canonical memory.

## Open gaps
- Gap: if the runtime grows more transports or public clients, create a dedicated runtime endpoint contract that defines `/mcp`, `/api/tools/{tool_name}`, authentication, and payload identity rejection in one place.
- Gap: if more frontend build registry rules accumulate, split the `NPM_REGISTRY_URL` and lockfile invariant into a small build/dependency contract instead of keeping it only in the web console module card.
