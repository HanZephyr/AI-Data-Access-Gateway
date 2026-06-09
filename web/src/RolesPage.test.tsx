// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
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
        description: "Existing warehouse description",
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
  "/admin/resource-tree": {
    ok: true,
    json: [
      {
        key: "resource:db_1",
        type: "resource",
        id: "db_1",
        datasource_id: "ds_1",
        name: "warehouse_db",
        display_name: "warehouse_db",
        kind: "database",
        children: [],
      },
    ],
  },
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
        reason: "allowed_by_policy",
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
  "/admin/api-keys": {
    ok: true,
    json: [
      {
        id: "key_1",
        name: "Console key",
        scopes: ["admin"],
        status: "active",
        created_at: "2026-04-26T10:00:00Z",
      },
    ],
  },
  "/admin/api-keys/key_1/revoke": { ok: true, json: {} },
  "/admin/users/importers/feishu/pull": {
    ok: true,
    json: {
      users: [
        {
          user_name: "Alice",
          external_ref: "u001",
          org_path: null,
          roles: [],
          action: "create",
        },
      ],
      org_nodes_to_create: [],
      roles_to_create: [],
      root_org_node_required: false,
      summary: { create_count: 1, update_count: 0 },
    },
  },
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

async function mountConsoleApp(initialPage: string, language = "en-US") {
  vi.resetModules();
  document.body.innerHTML = '<div id="root"></div>';
  const storage = createStorage();
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("matchMedia", createMatchMedia());
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: createMatchMedia(),
  });
  localStorage.setItem("adg.language", language);
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
  const input = await screen.findByPlaceholderText(/Paste the key printed by init-admin|输入 init-admin 输出的密钥|輸入 init-admin 輸出的金鑰/);
  fireEvent.change(input, {
    target: { value: "adg_admin" },
  });
  expect(input).toHaveValue("adg_admin");
  fireEvent.click(screen.getByRole("button", { name: /Sign In|登录控制台|登入控制台/ }));
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
    const linkedUsersButton = screen.getByRole("button", { name: "View linked users" });
    expect(linkedUsersButton).toBeInTheDocument();
    expect(linkedUsersButton.textContent).toBe("");

    fireEvent.click(linkedUsersButton);
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  }, 30000);

  it("shows datasource secret placeholders and omits unchanged passwords from update payloads", async () => {
    await mountConsoleApp("datasources");
    await signInWithValidAdminKey();

    const datasourceNode = await screen.findByText("Warehouse");
    expect(screen.queryByText("warehouse_db")).not.toBeInTheDocument();
    fireEvent.click(datasourceNode);

    const passwordInput = await screen.findByLabelText("Password");
    expect(passwordInput).toHaveAttribute("placeholder", "••••••••");

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(lastDatasourcePatchBody).not.toBeNull();
    });
    expect(lastDatasourcePatchBody).not.toHaveProperty("config.password");
  }, 30000);

  it("allows datasource database to stay blank and saves the operator description", async () => {
    await mountConsoleApp("datasources");
    await signInWithValidAdminKey();

    const datasourceNode = await screen.findByText("Warehouse");
    fireEvent.click(datasourceNode);

    expect(screen.queryByText("Use explicit connection fields instead of pasting JSON.")).not.toBeInTheDocument();

    fireEvent.change(await screen.findByLabelText("Database"), { target: { value: "" } });
    fireEvent.change(await screen.findByLabelText("Description"), {
      target: { value: "Use for curated finance and operations datasets." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(lastDatasourcePatchBody).not.toBeNull();
    });
    expect(lastDatasourcePatchBody).toHaveProperty(
      "description",
      "Use for curated finance and operations datasets.",
    );
    expect(lastDatasourcePatchBody).not.toHaveProperty("config.database");
  }, 30000);

  it("keeps audit rows summary-only and loads raw SQL on demand", async () => {
    await mountConsoleApp("audit");
    await signInWithValidAdminKey();

    expect(await screen.findByText("query_1")).toBeInTheDocument();
    expect(screen.queryByText("select id from public.customers limit 1")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View SQL" })).not.toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input) === "/admin/audit-events/event_1/sql")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "View audit log details" }));
    expect(await screen.findByText("Raw query SQL")).toBeInTheDocument();
    expect(await screen.findByText("select id from public.customers limit 1")).toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input) === "/admin/audit-events/event_1/sql")).toBe(true);
  }, 30000);

  it("localizes audit detail decision and reason labels in Simplified Chinese", async () => {
    await mountConsoleApp("audit", "zh-CN");
    await signInWithValidAdminKey();

    expect(await screen.findByText("query_1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看审计日志详情" }));

    await screen.findByText("原始查询 SQL");
    expect(screen.getAllByText("决策").length).toBeGreaterThan(0);
    expect(screen.getAllByText("原因").length).toBeGreaterThan(0);
    expect(screen.getAllByText("允许").length).toBeGreaterThan(0);
  }, 30000);

  it("labels the API key revoke icon action", async () => {
    await mountConsoleApp("apiKeys");
    await signInWithValidAdminKey();

    expect(await screen.findByText("Console key")).toBeInTheDocument();
    const revokeButton = screen.getByRole("button", { name: "Revoke" });
    expect(revokeButton).toBeInTheDocument();
    expect(revokeButton.textContent).toBe("");
  }, 30000);

  it("shows hyphen placeholders for empty org path and roles in import preview", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    fireEvent.click(await screen.findByText("Import user data"));
    fireEvent.click(screen.getByRole("tab", { name: "Feishu" }));
    fireEvent.click(screen.getByRole("button", { name: "Preview import" }));

    const externalRefCell = await screen.findByRole("cell", { name: "u001" });
    const row = externalRefCell.closest("tr");
    expect(row).not.toBeNull();
    const cells = row ? Array.from(row.querySelectorAll("td")) : [];
    expect(cells).toHaveLength(4);
    expect(cells[2]).toHaveTextContent("-");
    expect(cells[3]).toHaveTextContent("-");

    const keyStat = screen.getByText("Runtime keys created").closest(".ant-statistic");
    expect(keyStat).not.toBeNull();
    expect(keyStat).toHaveTextContent("1");
  }, 30000);

  it("filters directory users by selected org node using org path fallback", async () => {
    routeMap["/admin/org-nodes"] = {
      ok: true,
      json: [
        { id: "org_root", name: "Root", path: "", parent_id: null, status: "active" },
        { id: "org_finance", name: "Finance", path: "Company/Finance", parent_id: "org_root", status: "active" },
      ],
    };
    routeMap["/admin/users"] = {
      ok: true,
      json: [
        {
          id: "user_1",
          user_id: "user_1",
          name: "Alice",
          external_ref: "u001",
          org_node_id: null,
          org_path: "Company/Finance",
          role_ids: [],
          role_names: [],
          status: "active",
        },
      ],
    };

    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    const listPanelHeading = await screen.findAllByText("User directory");
    const listPanel = listPanelHeading[1]?.closest("section");
    expect(listPanel).not.toBeNull();

    expect(await within(listPanel as HTMLElement).findByRole("cell", { name: "u001" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("img", { name: "caret-down" }));
    fireEvent.click(await screen.findByText("Finance"));
    expect(await within(listPanel as HTMLElement).findByRole("cell", { name: "u001" })).toBeInTheDocument();
  }, 30000);
});
