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
  "/admin/resources": { ok: true, json: [] },
  "/admin/tags": { ok: true, json: [] },
  "/admin/resource-policies": { ok: true, json: [] },
  "/admin/field-policies": { ok: true, json: [] },
  "/admin/audit-events": { ok: true, json: [] },
  "/admin/org-nodes": {
    ok: true,
    json: [
      { id: "org_root", name: "Root", parent_id: null, path: "", depth: 0, status: "active", direct_user_names: [] },
      { id: "org_company", name: "Company", parent_id: "org_root", path: "Company", depth: 1, status: "active", direct_user_names: [] },
      { id: "org_finance", name: "Finance", parent_id: "org_company", path: "Company/Finance", depth: 2, status: "active", direct_user_names: ["Alice"] },
    ],
  },
  "/admin/roles": {
    ok: true,
    json: [
      { id: "role_analyst", name: "Analyst", description: null, status: "active" },
      { id: "role_reviewer", name: "Reviewer", description: null, status: "active" },
    ],
  },
  "/admin/users": {
    ok: true,
    json: [
      {
        id: "user_1",
        name: "Alice",
        external_ref: "u001",
        org_node_id: "org_finance",
        org_path: "Company/Finance",
        role_ids: ["role_analyst"],
        role_names: ["Analyst"],
        status: "active",
      },
    ],
  },
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

async function mountConsoleApp(initialPage?: string) {
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
  if (initialPage) {
    localStorage.setItem("adg.page", initialPage);
  }
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
  const input = await screen.findByPlaceholderText("Paste the key printed by init-admin");
  fireEvent.change(input, {
    target: { value: "adg_admin" },
  });
  expect(input).toHaveValue("adg_admin");
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
}

async function resizeWindow(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  fireEvent(window, new Event("resize"));
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("Users console page", () => {
  it("does not write the admin key to localStorage after sign-in", async () => {
    await mountConsoleApp("users");

    expect(localStorage.getItem("adg.apiKey")).toBeNull();
    await signInWithValidAdminKey();
    expect(localStorage.getItem("adg.apiKey")).toBeNull();
    expect(await screen.findByText("Organization tree")).toBeInTheDocument();
  }, 10000);

  it("shows a users navigation item and no standalone organization page", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect((await screen.findAllByText("Users")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Roles").length).toBeGreaterThan(0);
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
  }, 10000);

  it("opens the excel import modal with click and drag upload affordances", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByText("Import user data"));

    expect((await screen.findAllByText("Upload file")).length).toBeGreaterThan(0);
    expect(screen.getByText("Drag file here")).toBeInTheDocument();
    expect(screen.getByLabelText("Organization path delimiter")).toBeInTheDocument();
  });

  it("shows localized field guidance and credential-based third-party import tabs in the import modal", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByText("Import user data"));

    expect(await screen.findByText("Download template")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Download template/i })).toHaveAttribute(
      "href",
      "/adg-user-import-template.xlsx",
    );
    expect(screen.getByText("user_name")).toBeInTheDocument();
    expect(screen.getByText("external_ref")).toBeInTheDocument();
    expect(screen.getByText("Feishu")).toBeInTheDocument();
    expect(screen.getByText("WeCom")).toBeInTheDocument();
    expect(screen.getByText("DingTalk")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Feishu"));
    expect((await screen.findAllByText("App ID")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("App secret").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Root department ID").length).toBeGreaterThan(0);
    expect(screen.queryByText("Departments response")).not.toBeInTheDocument();
    expect(screen.queryByText("Users response")).not.toBeInTheDocument();
  });

  it("renders the rooted org tree and user detail workspace on the users page", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect(await screen.findByText("Organization tree")).toBeInTheDocument();
    expect(screen.getByText("/")).toBeInTheDocument();
    expect(screen.getAllByText("User directory").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Alice").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByText("Runtime key")).toBeInTheDocument();
    });
  });

  it("opens context actions from the org tree nodes instead of top toolbar icons", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect(await screen.findByText("/")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh" })).not.toBeInTheDocument();

    fireEvent.contextMenu(screen.getByText("/"));
    expect(await screen.findByText("Create node")).toBeInTheDocument();
    expect(screen.queryByText("Delete node")).not.toBeInTheDocument();
  });

  it("opens a left-side navigation drawer on small screens", async () => {
    await mountConsoleApp("overview");
    await signInWithValidAdminKey();
    await resizeWindow(860);

    fireEvent.click(await screen.findByRole("button", { name: "Open navigation" }));
    expect(document.querySelector(".ant-drawer-left")).not.toBeNull();
    expect((await screen.findAllByText("Policies")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByText("Users")[0]);
    await waitFor(() => {
      expect(screen.getAllByText("Users").length).toBeGreaterThan(0);
    });
  });
});
