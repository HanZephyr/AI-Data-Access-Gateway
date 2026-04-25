// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const routeMap: Record<string, unknown> = {
  "/admin/datasources": [],
  "/admin/resources": [],
  "/admin/audit-events": [],
  "/admin/roles": [
    { id: "role_analyst", name: "Analyst", description: "Finance analysts", status: "active" },
    { id: "role_reviewer", name: "Reviewer", description: "Approval reviewers", status: "active" },
  ],
  "/admin/org-nodes": [],
  "/admin/users": [],
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
  localStorage.setItem("adg.apiKey", "adg_admin");
  if (initialPage) {
    localStorage.setItem("adg.page", initialPage);
  }
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (!(url in routeMap)) {
      return {
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ detail: "Not Found" }),
        text: async () => "Not Found",
      } as Response;
    }
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => routeMap[url],
      text: async () => JSON.stringify(routeMap[url]),
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

describe("Roles console page", () => {
  it("renders a dedicated roles page with independent content", async () => {
    await mountConsoleApp("roles");

    expect(await screen.findByText("Role directory")).toBeInTheDocument();
    expect(await screen.findByText("Analyst")).toBeInTheDocument();
    expect(await screen.findByText("Reviewer")).toBeInTheDocument();
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
  }, 10000);
});
