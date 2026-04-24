# Acceptance Criteria: Milestone 5 Web Console

**Spec:** `docs/superpowers/specs/2026-04-24-milestone-5-web-console-design.md`
**Date:** 2026-04-24
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | Admin resource browsing returns resources and fields. | API | Admin key and resource snapshot rows exist. | `/admin/resources` and `/admin/resources/{id}/fields` return scoped data. |
| AC-002 | Admin tag APIs create tags and bind them to resources. | API | Admin key and a resource exist. | Tag CRUD and binding endpoints persist expected rows. |
| AC-003 | Admin policy APIs manage resource and field policies. | API | Admin key exists. | Create/list/update/delete flows work for both policy types. |
| AC-004 | Admin masking policy APIs manage masking policies. | API | Admin key and a resource exist. | Create/list/update/delete flow works. |
| AC-005 | Admin API key APIs create and revoke keys. | API | Admin key exists. | A created key returns plaintext once and can be revoked. |
| AC-006 | Audit query returns stored audit events. | API | Audit event rows exist. | `/admin/audit-events` returns them in descending creation order. |
| AC-007 | MCP setup endpoint returns client-facing metadata. | API | Admin key exists. | `/admin/mcp/setup` returns URL, header name, and tool names. |
| AC-008 | Web console builds successfully. | Logic | Node dependencies are installed. | `npm run build` in `web/` exits 0. |
| AC-009 | Web console navigation is clickable in browser. | UI interaction | Vite dev server is running. | Overview and each management page render without console errors. |
