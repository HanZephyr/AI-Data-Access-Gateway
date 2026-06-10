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

const baseRouteMap: Record<string, MockResponse> = {
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
  "/admin/users/importers/feishu/pull": {
    ok: true,
    json: {
      summary: {
        created_users: 1,
        updated_users: 0,
        runtime_keys_created: 1,
      },
      org_nodes_to_create: [],
      roles_to_create: [],
      users: [
        {
          user_id: "user_2",
          user_name: "Imported User",
          external_ref: "u-imported",
          org_path: "Company/Finance",
          roles: ["Analyst"],
        },
      ],
    },
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
let routeMap: Record<string, MockResponse>;

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
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = String(init?.method || "GET").toUpperCase();
    if (url === "/admin/users/user_1" && method === "PATCH") {
      const body = JSON.parse(String(init?.body || "{}")) as {
        name?: string;
        external_ref?: string;
        org_node_id?: string | null;
        role_ids?: string[];
        status?: string;
      };
      const users = Array.isArray(routeMap["/admin/users"]?.json)
        ? [...(routeMap["/admin/users"]?.json as Array<Record<string, unknown>>)]
        : [];
      const nextUsers = users.map((user) => {
        if (user.id !== "user_1") return user;
        const orgPath = body.org_node_id === "org_company"
          ? "Company"
          : body.org_node_id === "org_finance"
            ? "Company/Finance"
            : null;
        const roleNames = (body.role_ids || []).map((roleId) => (
          roleId === "role_reviewer" ? "Reviewer" : "Analyst"
        ));
        return {
          ...user,
          name: body.name ?? user.name,
          external_ref: body.external_ref ?? user.external_ref,
          org_node_id: body.org_node_id ?? user.org_node_id,
          org_path: orgPath ?? user.org_path,
          role_ids: body.role_ids ?? user.role_ids,
          role_names: roleNames.length ? roleNames : user.role_names,
          status: body.status ?? user.status,
        };
      });
      routeMap["/admin/users"] = { ok: true, json: nextUsers };
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => nextUsers.find((user) => user.id === "user_1"),
        text: async () => JSON.stringify(nextUsers.find((user) => user.id === "user_1")),
      } as Response;
    }
    if (url === "/admin/users/user_1" && method === "DELETE") {
      const users = Array.isArray(routeMap["/admin/users"]?.json)
        ? (routeMap["/admin/users"]?.json as Array<Record<string, unknown>>)
        : [];
      routeMap["/admin/users"] = {
        ok: true,
        json: users.filter((user) => user.id !== "user_1"),
      };
      return {
        ok: true,
        status: 204,
        statusText: "No Content",
        json: async () => undefined,
        text: async () => "",
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

async function resizeWindow(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  fireEvent(window, new Event("resize"));
}

beforeEach(() => {
  vi.unstubAllGlobals();
  routeMap = JSON.parse(JSON.stringify(baseRouteMap)) as Record<string, MockResponse>;
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

describe("Users console page", () => {
  it("does not write the admin key to localStorage after sign-in", async () => {
    await mountConsoleApp("users");

    expect(localStorage.getItem("adg.apiKey")).toBeNull();
    await signInWithValidAdminKey();
    expect(localStorage.getItem("adg.apiKey")).toBeNull();
    expect(await screen.findByText("Organization tree")).toBeInTheDocument();
  }, 30000);

  it("shows a users navigation item and no standalone organization page", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect((await screen.findAllByText("Users")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Roles").length).toBeGreaterThan(0);
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
  }, 30000);

  it("opens the excel import modal with click and drag upload affordances", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByText("Import user data"));

    expect((await screen.findAllByText("Upload file")).length).toBeGreaterThan(0);
    expect(screen.getByText("Drag file here")).toBeInTheDocument();
    expect(screen.getByLabelText("Organization path delimiter")).toBeInTheDocument();
  }, 30000);

  it("keeps the selected Excel file inside the dragger without rendering a separate upload list", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByText("Import user data"));

    const uploadInput = document.querySelector('input[type="file"]');
    expect(uploadInput).not.toBeNull();

    const file = new File(["name,external_ref\nAlice,u001"], "users.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    fireEvent.change(uploadInput as HTMLInputElement, { target: { files: [file] } });

    expect((await screen.findAllByText("users.xlsx")).length).toBeGreaterThan(0);
    expect(document.querySelector(".ant-upload-list")).toBeNull();
  }, 30000);

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
  }, 30000);

  it("closes the import modal after a successful execute import", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByText("Import user data"));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Feishu" }));
    expect((await screen.findAllByText("App ID")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Execute import" }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).not.toBeVisible();
    });
  }, 30000);

  it("renders the rooted org tree and user detail workspace on the users page", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect(await screen.findByText("Organization tree")).toBeInTheDocument();
    expect(await screen.findByText("/", {}, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.getAllByText("User directory").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Alice").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByText("Runtime key")).toBeInTheDocument();
    });
  }, 30000);

  it("edits the selected user from the details panel", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    await screen.findByText("Runtime key", {}, { timeout: 10000 });

    fireEvent.click(await screen.findByRole("button", { name: "Edit" }));
    const drawer = await screen.findByRole("dialog", { name: "Edit Users" });
    fireEvent.change(within(drawer).getByDisplayValue("Alice"), { target: { value: "Alice Updated" } });
    fireEvent.change(within(drawer).getByDisplayValue("u001"), { target: { value: "u009" } });
    fireEvent.click(within(drawer).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getAllByText("Alice Updated").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("u009").length).toBeGreaterThan(0);
  }, 30000);

  it("deletes the selected user from the details panel", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();
    await screen.findByText("Runtime key", {}, { timeout: 10000 });

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    const deleteConfirmButtons = await screen.findAllByRole("button", { name: "Delete" });
    fireEvent.click(deleteConfirmButtons[deleteConfirmButtons.length - 1]);

    await waitFor(() => {
      expect(screen.getByText("Select a user to inspect roles, organization placement, and runtime key actions.")).toBeInTheDocument();
    });
  }, 30000);

  it("opens context actions from the org tree nodes instead of top toolbar icons", async () => {
    await mountConsoleApp("users");
    await signInWithValidAdminKey();

    expect(await screen.findByText("/", {}, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh" })).not.toBeInTheDocument();

    fireEvent.contextMenu(screen.getByText("/"));
    expect(await screen.findByText("Create node")).toBeInTheDocument();
    expect(screen.queryByText("Delete node")).not.toBeInTheDocument();
  }, 30000);

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
  }, 30000);
});
