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
        id: "ds_doris",
        name: "Doris Warehouse",
        type: "doris",
        datasource_kind: "relational",
        config: {
          host: "10.0.0.1",
          port: 9030,
          database: "warehouse",
          username: "reader",
          password: { kind: "secret_placeholder", configured: true },
        },
        status: "active",
        tags: [],
      },
    ],
  },
  "/admin/resource-tree": { ok: true, json: { items: [], total: 0, limit: 50, offset: 0 } },
  "/admin/tags": { ok: true, json: [] },
  "/admin/datasources/ds_doris/test": {
    ok: false,
    status: 400,
    statusText: "Bad Request",
    json: { detail: "Connector cannot reach Doris" },
    text: '{"detail":"Connector cannot reach Doris"}',
  },
  "/admin/datasources/ds_doris/scan": {
    ok: false,
    status: 400,
    statusText: "Bad Request",
    json: { detail: "NullType() takes no arguments" },
    text: '{"detail":"NullType() takes no arguments"}',
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

async function mountConsoleApp() {
  vi.resetModules();
  document.body.innerHTML = '<div id="root"></div>';
  vi.stubGlobal("localStorage", createStorage());
  vi.stubGlobal("matchMedia", createMatchMedia());
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: createMatchMedia(),
  });
  localStorage.setItem("adg.language", "en-US");
  localStorage.setItem("adg.page", "datasources");
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const baseUrl = url.split("?")[0];
    const match = routeMap[url] ?? routeMap[baseUrl];
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
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
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

describe("Datasource action feedback", () => {
  it("shows backend errors from test and scan actions", async () => {
    await mountConsoleApp();
    await signInWithValidAdminKey();
    fireEvent.click(await screen.findByRole("menuitem", { name: /Data Sources/ }));
    const datasourceTitle = await screen.findByText("Doris Warehouse");
    fireEvent.click(datasourceTitle.closest(".ant-tree-node-content-wrapper") || datasourceTitle);

    fireEvent.click(await screen.findByText("Test"));
    expect(await screen.findByText("Connector cannot reach Doris")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: /Sync metadata/ }));
    await waitFor(() => {
      expect(screen.getByText("NullType() takes no arguments")).toBeInTheDocument();
    });
  }, 120000);
});
