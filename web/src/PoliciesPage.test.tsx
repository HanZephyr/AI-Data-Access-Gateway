// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type MockResponse = {
  ok: boolean;
  status?: number;
  statusText?: string;
  json?: unknown;
  text?: string;
};

const routeMap: Record<string, MockResponse> = {
  "/admin/system": { ok: true, json: { service_name: "AI Data Access Gateway" } },
  "/admin/datasources": { ok: true, json: [] },
  "/admin/resources": {
    ok: true,
    json: [
      {
        id: "res_finance",
        display_name: "Finance Orders",
        name: "orders",
        path: "warehouse.finance.orders",
        kind: "relational_table",
      },
    ],
  },
  "/admin/tags": {
    ok: true,
    json: [{ id: "tag_finance", name: "Finance", category: "domain", description: null }],
  },
  "/admin/resource-policies": { ok: true, json: [] },
  "/admin/field-policies": { ok: true, json: [] },
  "/admin/masking-policies": { ok: true, json: [] },
  "/admin/org-nodes": { ok: true, json: [] },
  "/admin/users": {
    ok: true,
    json: [
      {
        id: "user_1",
        name: "Alice",
        external_ref: "u001",
        org_node_id: null,
        org_path: null,
        role_ids: ["role_analyst"],
        role_names: ["Analyst"],
        status: "active",
      },
    ],
  },
  "/admin/roles": {
    ok: true,
    json: [{ id: "role_analyst", name: "Analyst", description: null, status: "active" }],
  },
  "/admin/api-keys": { ok: true, json: [] },
  "/admin/audit-events": { ok: true, json: [] },
  "/admin/mcp/setup": {
    ok: true,
    json: {
      server_url: "http://127.0.0.1:8000/mcp",
      http_tool_url_template: "http://127.0.0.1:8000/api/tools/{tool_name}",
      api_key_header: "X-ADG-API-Key",
      tools: [],
    },
  },
};

function createStorage() {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
}

function createMatchMedia() {
  return (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  });
}

async function mountConsoleApp(initialPage: string) {
  vi.resetModules();
  document.body.innerHTML = '<div id="root"></div>';
  const storage = createStorage();
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("matchMedia", createMatchMedia());
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: createMatchMedia(),
  });
  localStorage.setItem("adg.language", "en-US");
  localStorage.setItem("adg.apiKey", "adg_admin");
  localStorage.setItem("adg.page", initialPage);
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const match = routeMap[url];
    if (!match) {
      return {
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ detail: "Not Found" }),
        text: async () => "Not Found",
      } as Response;
    }
    return {
      ok: match.ok,
      status: match.status ?? 200,
      statusText: match.statusText ?? "OK",
      json: async () => match.json,
      text: async () => match.text ?? JSON.stringify(match.json ?? {}),
    } as Response;
  });
  await import("./main");
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("Policies page", () => {
  it("lets admins target a tag and pick a user or role instead of typing raw ids", async () => {
    await mountConsoleApp("policies");

    await waitFor(() => {
      expect(screen.getAllByText("Policies").length).toBeGreaterThan(0);
    });
    fireEvent.click(await screen.findByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(screen.getAllByText("Subject type").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Subject").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Tag").length).toBeGreaterThan(0);
    });
  }, 10000);
});
