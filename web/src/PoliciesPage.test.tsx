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

const POLICY_TEST_TIMEOUT_MS = 60000;

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
      {
        id: "ds_doris",
        name: "线上 Doris",
        type: "doris",
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
      {
        id: "res_doris_database",
        datasource_id: "ds_doris",
        parent_id: null,
        display_name: "ai_test",
        name: "ai_test",
        path: "ai_test",
        kind: "database",
      },
      {
        id: "res_doris_table",
        datasource_id: "ds_doris",
        parent_id: "res_doris_database",
        display_name: "dwd_shop_life_cycle",
        name: "dwd_shop_life_cycle",
        path: "ai_test.dwd_shop_life_cycle",
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
        id: "subject:WyJyb2xlIiwicm9sZV9hbmFseXN0Il0",
        policy_ids: ["policy_datasource", "policy_resource"],
        policy_count: 2,
        datasource_count: 1,
        resource_count: 1,
        tag_count: 0,
        subject_type: "role",
        subject_id: "role_analyst",
        subject_label: "Analyst",
        effect: "allow",
        action: "read",
        allow_decrypt: true,
        datasource_id: "ds_doris",
        datasource_ids: ["ds_doris"],
        datasource_label: "线上 Doris",
        datasource_labels: ["线上 Doris"],
        tag_id: null,
        tag_ids: [],
        tag_name: null,
        tag_names: [],
        resource_id: "res_long_table",
        resource_ids: ["res_long_table"],
        resource_label: "dws_ecommerce_order_overdue_detail_2025",
        resource_labels: ["dws_ecommerce_order_overdue_detail_2025"],
        status: "active",
        policy_items: [
          {
            id: "policy_datasource",
            subject_type: "role",
            subject_id: "role_analyst",
            subject_label: "Analyst",
            effect: "allow",
            action: "read",
            allow_decrypt: true,
            datasource_id: "ds_doris",
            datasource_label: "线上 Doris",
            tag_id: null,
            tag_name: null,
            resource_id: null,
            resource_label: null,
            status: "active",
          },
          {
            id: "policy_resource",
            subject_type: "role",
            subject_id: "role_analyst",
            subject_label: "Analyst",
            effect: "allow",
            action: "read",
            allow_decrypt: true,
            datasource_id: null,
            datasource_label: null,
            tag_id: null,
            tag_name: null,
            resource_id: "res_long_table",
            resource_label: "dws_ecommerce_order_overdue_detail_2025",
            status: "active",
          },
        ],
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
    const drawerText = document.querySelector(".ant-drawer-content")?.textContent || "";
    const detailLabels = Array.from(document.querySelectorAll(".ant-descriptions-item-label"))
      .map((item) => item.textContent || "");
    expect(drawerText).toContain("主体");
    expect(detailLabels).toContain("权限范围");
    expect(detailLabels).not.toContain("数据源");
    expect(detailLabels).not.toContain("资源");
    expect(drawerText).toContain("允许解密");
    const scopeTree = document.querySelector(".resource-policy-scope-tree");
    expect(scopeTree).toBeInTheDocument();
    if (!scopeTree) {
      throw new Error("missing resource policy scope tree");
    }
    expect(drawerText).toContain("线上 Doris");
    const getScopeNodeTitle = (name: string) => {
      const nodeText = Array.from(scopeTree.querySelectorAll(".resource-tree-node-title"))
        .find((item) => item.textContent === name);
      if (!(nodeText instanceof HTMLElement)) {
        throw new Error(`missing scope tree node: ${name}`);
      }
      return nodeText;
    };
    const getScopeSwitcher = (name: string) => {
      const nodeText = getScopeNodeTitle(name);
      const node = nodeText.closest(".ant-tree-treenode");
      const switcher = node?.querySelector(".ant-tree-switcher");
      expect(switcher).toBeInTheDocument();
      expect(switcher).not.toHaveClass("ant-tree-switcher-noop");
      return switcher as HTMLElement;
    };
    const toggleScopeNode = (name: string) => {
      const wrapper = getScopeNodeTitle(name).closest(".resource-policy-scope-tree-title");
      expect(wrapper).toBeInTheDocument();
      fireEvent.click(wrapper as HTMLElement);
    };
    await waitFor(() => {
      const currentDrawerText = document.querySelector(".ant-drawer-content")?.textContent || "";
      expect(currentDrawerText).toContain("Demo Warehouse");
      expect(currentDrawerText).not.toContain("dws_ecommerce_order_overdue_detail_2025");
      expect(getScopeSwitcher("Demo Warehouse")).toHaveClass("ant-tree-switcher_close");
    });
    toggleScopeNode("Demo Warehouse");
    await waitFor(() => {
      expect(scopeTree).toHaveTextContent("warehouse");
      expect(getScopeSwitcher("Demo Warehouse")).toHaveClass("ant-tree-switcher_open");
    });
    toggleScopeNode("Demo Warehouse");
    await waitFor(() => {
      expect(getScopeSwitcher("Demo Warehouse")).toHaveClass("ant-tree-switcher_close");
    });
    for (const rawKey of ["subject_label", "resource_label", "allow_decrypt"]) {
      if (drawerText.includes(rawKey)) {
        throw new Error(`unexpected raw detail key: ${rawKey}`);
      }
    }
  }, POLICY_TEST_TIMEOUT_MS);

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
  }, POLICY_TEST_TIMEOUT_MS);

  it("loads every grouped resource authorization when editing one subject row", async () => {
    await mountConsoleApp("policies", "zh-CN");
    await signInWithValidAdminKey();

    await waitFor(() => {
      expect(screen.getByText("Analyst")).toBeInTheDocument();
      expect(screen.getByText("1 行")).toBeInTheDocument();
      const policyTableText = document.querySelector(".ant-table")?.textContent || "";
      expect(policyTableText).toContain("1 项");
      expect((policyTableText.match(/1 项/g) || []).length).toBeGreaterThanOrEqual(2);
      expect(policyTableText).not.toContain("线上 Doris");
      expect(policyTableText).not.toContain("dws_ecommerce_order_overdue_detail_2025");
    }, { timeout: 10000 });

    fireEvent.click(screen.getByRole("button", { name: "编辑" }));

    await screen.findByText("编辑资源权限策略");
    const transferLists = document.querySelectorAll(".resource-tree-transfer .ant-transfer-list");
    expect(transferLists[1]?.textContent).toContain("2");
    expect(transferLists[1]?.textContent).toContain("项");

    const selectedExpandButton = Array.from(
      document.querySelectorAll(".resource-tree-transfer .ant-transfer-list:nth-child(3) button"),
    ).find((button) => button.getAttribute("aria-label") === "已选资源 全部展开");
    expect(selectedExpandButton).toBeInstanceOf(HTMLElement);
    fireEvent.click(selectedExpandButton as HTMLElement);

    await waitFor(() => {
      expect(transferLists[1]?.textContent).toContain("线上 Doris");
      expect(transferLists[1]?.textContent).toContain("dws_ecommerce_order_overdue_detail_2025");
    });
  }, POLICY_TEST_TIMEOUT_MS);

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
    expect(transfer?.textContent).toContain("Demo Warehouse");
    expect(transfer?.textContent).toContain("线上 Doris");
    expect(screen.getByText("8 项")).toBeInTheDocument();
    expect(transfer?.textContent).not.toContain("warehouse");
    expect(transfer?.textContent).not.toContain("dws_ecommerce_order_overdue_detail_2025");
    expect(transfer?.textContent).not.toMatch(/database:/);
    expect(transfer?.textContent).not.toMatch(/table:/);
    expect(screen.getAllByRole("button", { name: /全部展开/ })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /全部折叠/ })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "已选资源 全部展开" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "已选资源 全部折叠" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "可选资源 全部展开" }));
    expect(await screen.findByText("warehouse")).toBeInTheDocument();
    expect(await screen.findByText("finance")).toBeInTheDocument();
    expect(await screen.findByText("Finance Orders")).toBeInTheDocument();
    await waitFor(() => {
      expect(transfer?.textContent).toContain("dws_ecommerce_order_overdue_detail_2025");
    });
    expect(await screen.findByText("ai_test")).toBeInTheDocument();
    expect(await screen.findByText("dwd_shop_life_cycle")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "可选资源 全部折叠" }));
    expect(screen.queryByText("warehouse")).not.toBeInTheDocument();
    expect(screen.queryByText("ai_test")).not.toBeInTheDocument();

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
    fireEvent.change(searchInput!, { target: { value: "warehouse" } });
    expect(await screen.findByText("warehouse")).toBeInTheDocument();
    expect(screen.queryByText("finance")).not.toBeInTheDocument();
    expect(transfer?.textContent).not.toContain("dws_ecommerce_order_overdue_detail_2025");

    fireEvent.change(searchInput!, { target: { value: "overdue_detail" } });

    expect(await screen.findByText("warehouse")).toBeInTheDocument();
    expect(await screen.findByText("finance")).toBeInTheDocument();
    await waitFor(() => {
      expect(transfer?.textContent).toContain("dws_ecommerce_order_overdue_detail_2025");
    });

    expect(document.querySelector(".resource-tree-transfer .ant-transfer-operation button")).toBeInTheDocument();
  }, POLICY_TEST_TIMEOUT_MS);
});
