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
        id: "ds_warehouse",
        name: "Demo Warehouse",
        type: "postgres",
        datasource_kind: "relational",
        status: "active",
      },
    ],
  },
  "/admin/resources": {
    ok: true,
    json: [
      {
        id: "res_database",
        datasource_id: "ds_warehouse",
        parent_id: null,
        display_name: "warehouse",
        name: "warehouse",
        path: "warehouse",
        kind: "database",
      },
      {
        id: "res_schema",
        datasource_id: "ds_warehouse",
        parent_id: "res_database",
        display_name: "finance",
        name: "finance",
        path: "warehouse.finance",
        kind: "schema",
      },
      {
        id: "res_finance",
        datasource_id: "ds_warehouse",
        parent_id: "res_schema",
        display_name: "Finance Orders",
        name: "orders",
        path: "warehouse.finance.orders",
        kind: "relational_table",
      },
      {
        id: "res_long_table",
        datasource_id: "ds_warehouse",
        parent_id: "res_schema",
        display_name: "dws_ecommerce_order_overdue_detail_2025",
        name: "dws_ecommerce_order_overdue_detail_2025",
        path: "warehouse.finance.dws_ecommerce_order_overdue_detail_2025",
        kind: "relational_table",
      },
    ],
  },
  "/admin/tags": {
    ok: true,
    json: [{ id: "tag_finance", name: "Finance", category: "domain", description: null }],
  },
  "/admin/resource-policies": {
    ok: true,
    json: [
      {
        id: "policy_1",
        subject_type: "role",
        subject_id: "role_analyst",
        subject_label: "Analyst",
        effect: "allow",
        action: "read",
        allow_decrypt: true,
        datasource_id: null,
        datasource_label: null,
        tag_id: "tag_finance",
        tag_name: "Finance",
        resource_id: null,
        resource_label: null,
        status: "active",
      },
    ],
  },
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

describe("Policies page", () => {
  it("localizes resource policy detail labels in Simplified Chinese", async () => {
    await mountConsoleApp("policies", "zh-CN");
    await signInWithValidAdminKey();

    expect(await screen.findByText("Analyst")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看" }));

    await screen.findByText("资源权限策略详情");
    expect(screen.getAllByText("主体").length).toBeGreaterThan(0);
    expect(screen.getAllByText("标签 ID").length).toBeGreaterThan(0);
    expect(screen.getAllByText("标签名称").length).toBeGreaterThan(0);
    expect(screen.getAllByText("允许解密").length).toBeGreaterThan(0);
    expect(screen.queryByText("subject_label")).not.toBeInTheDocument();
    expect(screen.queryByText("tag_name")).not.toBeInTheDocument();
    expect(screen.queryByText("allow_decrypt")).not.toBeInTheDocument();
  }, 30000);

  it("lets admins target a tag and pick a user or role instead of typing raw ids", async () => {
    await mountConsoleApp("policies");
    await signInWithValidAdminKey();

    fireEvent.click(await screen.findByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(screen.getAllByText("Subject type").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Subject").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Tag name").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Allow decrypt").length).toBeGreaterThan(0);
    });
    expect(screen.queryByText("Priority")).not.toBeInTheDocument();
  }, 30000);

  it("renders datasource and resource scopes as a tree transfer", async () => {
    await mountConsoleApp("policies", "zh-CN");
    await signInWithValidAdminKey();

    fireEvent.click(await screen.findByRole("button", { name: "新建" }));

    await waitFor(() => {
      expect(document.querySelector(".resource-tree-transfer")).toBeInTheDocument();
    });

    const transfer = document.querySelector(".resource-tree-transfer");
    expect(transfer).toBeInTheDocument();
    expect(document.querySelector(".resource-tree-transfer .ant-transfer-list")).toHaveStyle({ height: "360px" });
    expect(screen.getByText("Demo Warehouse")).toBeInTheDocument();
    expect(screen.getByText("5 项")).toBeInTheDocument();
    expect(screen.queryByText("warehouse")).not.toBeInTheDocument();
    expect(screen.queryByText("dws_ecommerce_order_overdue_detail_2025")).not.toBeInTheDocument();
    expect(screen.queryByText(/database:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/table:/)).not.toBeInTheDocument();

    const expandNode = async (name: string) => {
      const nodeText = await screen.findByText(name);
      const node = nodeText.closest(".ant-tree-treenode");
      const switcher = node?.querySelector(".ant-tree-switcher");
      expect(switcher).toBeInTheDocument();
      (switcher as HTMLElement).click();
    };
    await expandNode("Demo Warehouse");
    expect(await screen.findByText("warehouse")).toBeInTheDocument();

    const searchInput = document.querySelector(".resource-tree-transfer .ant-transfer-list-search input");
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute("placeholder", "搜索资源");
    fireEvent.change(searchInput!, { target: { value: "overdue_detail" } });

    expect(await screen.findByText("warehouse")).toBeInTheDocument();
    expect(await screen.findByText("finance")).toBeInTheDocument();
    expect(await screen.findByText("dws_ecommerce_order_overdue_detail_2025")).toBeInTheDocument();

    expect(document.querySelector(".resource-tree-transfer .ant-transfer-operation button")).toBeInTheDocument();
  }, 30000);
});
