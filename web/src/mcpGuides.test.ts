import { describe, expect, it } from "vitest";

import { buildMcpPlatformGuides } from "./mcpGuides";

const setup = {
  server_url: "https://gateway.example.com/mcp",
  http_tool_url_template: "https://gateway.example.com/api/tools/{tool_name}",
  api_key_header: "X-ADG-API-Key",
  tools: [
    { name: "list_datasources", description: "List readable datasources." },
    { name: "execute_query", description: "Run a read-only SQL query." }
  ]
};

describe("buildMcpPlatformGuides", () => {
  it("builds a Codex config snippet with the MCP server url and auth header", () => {
    const guides = buildMcpPlatformGuides(setup);
    const codex = guides.find((guide) => guide.key === "codex");

    expect(codex?.snippets[0]?.code).toContain("[mcp_servers.adg]");
    expect(codex?.snippets[0]?.code).toContain('url = "https://gateway.example.com/mcp"');
    expect(codex?.snippets[0]?.code).toContain("[mcp_servers.adg.http_headers]");
    expect(codex?.snippets[0]?.code).toContain('X-ADG-API-Key = "${ADG_RUNTIME_API_KEY}"');
  });

  it("builds a Claude Code project config snippet with remote HTTP headers", () => {
    const guides = buildMcpPlatformGuides(setup);
    const claudeCode = guides.find((guide) => guide.key === "claude-code");
    const jsonSnippet = claudeCode?.snippets.find((snippet) => snippet.label === "JSON");

    expect(jsonSnippet?.code).toContain('"type": "http"');
    expect(jsonSnippet?.code).toContain('"url": "https://gateway.example.com/mcp"');
    expect(jsonSnippet?.code).toContain('"X-ADG-API-Key": "${ADG_RUNTIME_API_KEY}"');
  });
});
