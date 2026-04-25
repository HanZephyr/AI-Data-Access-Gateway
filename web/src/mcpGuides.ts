export type McpSetupPayload = {
  server_url: string;
  http_tool_url_template: string;
  api_key_header: string;
  tools: Array<{ name: string; description: string }>;
};

export type McpGuideSnippet = {
  label: string;
  language: "toml" | "json" | "bash";
  code: string;
};

export type McpPlatformGuide = {
  key: "codex" | "claude-code" | "trae" | "mcporter";
  snippets: McpGuideSnippet[];
};

const runtimeEnvVar = "ADG_RUNTIME_API_KEY";

export function buildMcpPlatformGuides(setup: McpSetupPayload): McpPlatformGuide[] {
  const header = setup.api_key_header;
  const serverUrl = setup.server_url;

  return [
    {
      key: "codex",
      snippets: [
        {
          label: "config.toml",
          language: "toml",
          code: [
            "[mcp_servers.adg]",
            'enabled = true',
            `url = "${serverUrl}"`,
            "",
            "[mcp_servers.adg.http_headers]",
            `${header} = "\${${runtimeEnvVar}}"`,
          ].join("\n"),
        },
      ],
    },
    {
      key: "claude-code",
      snippets: [
        {
          label: "CLI",
          language: "bash",
          code: [
            "claude mcp add-json adg '",
            JSON.stringify(
              {
                type: "http",
                url: serverUrl,
                headers: {
                  [header]: `\${${runtimeEnvVar}}`,
                },
              },
              null,
              2,
            ),
            "'",
          ].join(""),
        },
        {
          label: "JSON",
          language: "json",
          code: JSON.stringify(
            {
              mcpServers: {
                adg: {
                  type: "http",
                  url: serverUrl,
                  headers: {
                    [header]: `\${${runtimeEnvVar}}`,
                  },
                },
              },
            },
            null,
            2,
          ),
        },
      ],
    },
    {
      key: "trae",
      snippets: [
        {
          label: ".trae/mcp.json",
          language: "json",
          code: JSON.stringify(
            {
              mcpServers: {
                adg: {
                  url: serverUrl,
                  headers: {
                    [header]: `\${${runtimeEnvVar}}`,
                  },
                },
              },
            },
            null,
            2,
          ),
        },
      ],
    },
    {
      key: "mcporter",
      snippets: [
        {
          label: "config/mcporter.json",
          language: "json",
          code: JSON.stringify(
            {
              mcpServers: {
                adg: {
                  description: "AI Data Access Gateway runtime tools",
                  baseUrl: serverUrl,
                  headers: {
                    [header]: `$env:${runtimeEnvVar}`,
                  },
                },
              },
            },
            null,
            2,
          ),
        },
      ],
    },
  ];
}
