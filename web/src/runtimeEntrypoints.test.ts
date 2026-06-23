import { describe, expect, it } from "vitest";

// @ts-expect-error Vite raw imports expose file source during Vitest runs.
import mainSource from "./main.tsx?raw";
// @ts-expect-error Vite raw imports expose file source during Vitest runs.
import viteConfigSource from "../vite.config.ts?raw";

describe("runtime entrypoints", () => {
  it("proxies the HTTP tool API through the local Vite dev server", () => {
    expect(viteConfigSource).toContain('"/api/tools": backendTarget');
  });

  it("labels the HTTP tool URL as a supplemental plain HTTP API", () => {
    expect(mainSource).not.toContain('"mcp.toolUrl": "Legacy HTTP facade"');
    expect(mainSource).toContain('"mcp.toolUrl": "Supplemental HTTP tool API"');
    expect(mainSource).toContain('"mcp.toolUrl": "补充普通 HTTP 工具地址"');
  });
});
