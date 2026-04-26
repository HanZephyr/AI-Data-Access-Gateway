// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type ReactDOM from "react-dom/client";

type MockResponse = {
  ok: boolean;
  status?: number;
  statusText?: string;
  json?: unknown;
  text?: string;
};

type WindowWithAppRoot = Window & {
  __adgRoot?: ReactDOM.Root;
  __adgRootElement?: HTMLElement | null;
};

const routeMap: Record<string, MockResponse> = {
  "/admin/system": { ok: true, json: { service_name: "AI Data Access Gateway" } },
  "/admin/datasources": {
    ok: true,
    json: [
      {
        id: "ds_1",
        name: "Warehouse",
        type: "postgres",
        datasource_kind: "relational",
        status: "active",
        config: {
          host: "db.internal",
          port: 5432,
          database: "warehouse",
          username: "analyst",
          password: { kind: "secret_placeholder", configured: true },
        },
        tags: [],
      },
    ],
  },
  "/admin/resources": { ok: true, json: [] },
  "/admin/resource-tree": { ok: true, json: [] },
  "/admin/tags": { ok: true, json: [] },
  "/admin/resource-policies": { ok: true, json: [] },
  "/admin/field-policies": { ok: true, json: [] },
  "/admin/masking-policies": { ok: true, json: [] },
  "/admin/audit-events": {
    ok: true,
    json: [
      {
        id: "event_1",
        event_type: "query_allowed",
        decision: "allowed",
        datasource_id: "ds_1",
        query_id: "query_1",
        created_at: "2026-04-26T10:00:00Z",
      },
    ],
  },
  "/admin/audit-events/event_1/sql": {
    ok: true,
    json: {
      id: "event_1",
      sql_text: "select id from public.customers limit 1",
    },
  },
  "/admin/org-nodes": { ok: true, json: [] },
  "/admin/users": { ok: true, json: [] },
  "/admin/api-keys": { ok: true, json: [] },
  "/admin/mcp/setup": {
    ok: true,
    json: {
      server_url: "http://127.0.0.1:8000/mcp",
      http_tool_url_template: "http://127.0.0.1:8000/api/tools/{tool_name}",
      api_key_header: "X-ADG-API-Key",
      tools: [],
    },
  },
  "/admin/roles": {
    ok: true,
    json: [
      {
        id: "role_analyst",
        name: "Analyst",
        description: "Finance analyst role",
        status: "active",
        user_count: 2,
      },
    ],
  },
  "/admin/roles/role_analyst/users": {
    ok: true,
    json: [
      {
        id: "user_1",
        name: "Alice",
        external_ref: "u001",
        org_path: "Company/Finance",
        role_names: ["Analyst"],
        status: "active",
      },
      {
        id: "user_2",
        name: "Bob",
        external_ref: "u002",
        org_path: "Company/Finance",
        role_names: ["Analyst"],
        status: "active",
      },
    ],
  },
};

let lastDatasourcePatchBody: Record<string, unknown> | null = null;

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
  localStorage.setItem("adg.page", initialPage);
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url === "/admin/datasources/ds_1" && init?.method === "PATCH") {
      lastDatasourcePatchBody = JSON.parse(String(init.body || "{}")) as Record<string, unknown>;
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({}),
        text: async () => "{}",
      } as Response;
    }
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

async function signInWithValidAdminKey() {
  const input = await screen.findByPlaceholderText("Paste the key printed by init-admin");
  fireEvent.change(input, {
    target: { value: "adg_admin" },
  });
  expect(input).toHaveValue("adg_admin");
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
}

beforeEach(() => {
  vi.unstubAllGlobals();
  lastDatasourcePatchBody = null;
});

afterEach(() => {
  const appWindow = window as WindowWithAppRoot;
  appWindow.__adgRoot?.unmount();
  appWindow.__adgRoot = undefined;
  appWindow.__adgRootElement = undefined;
  cleanup();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("Roles page", () => {
  it("supports role CRUD entry points and linked user details", async () => {
    await mountConsoleApp("roles");
    await signInWithValidAdminKey();

    expect(await screen.findByText("Role directory")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create/ })).toBeInTheDocument();
    expect(await screen.findByText("Analyst")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View linked users" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View linked users" }));
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  }, 20000);

  it("shows datasource secret placeholders and omits unchanged passwords from update payloads", async () => {
    await mountConsoleApp("datasources");
    await signInWithValidAdminKey();

    fireEvent.click(await screen.findByText("Warehouse"));

    const passwordInput = await screen.findByLabelText("Password");
    expect(passwordInput).toHaveAttribute("placeholder", "••••••••");

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(lastDatasourcePatchBody).not.toBeNull();
    });
    expect(lastDatasourcePatchBody).not.toHaveProperty("config.password");
  }, 20000);

  it("keeps audit rows summary-only and loads raw SQL on demand", async () => {
    await mountConsoleApp("audit");
    await signInWithValidAdminKey();

    expect(await screen.findByText("query_1")).toBeInTheDocument();
    expect(screen.queryByText("select id from public.customers limit 1")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View SQL" }));
    expect(await screen.findByText("select id from public.customers limit 1")).toBeInTheDocument();
  }, 20000);
});
