import { describe, expect, it, vi } from "vitest";

import { validateAdminApiKey } from "./adminAuth";

describe("validateAdminApiKey", () => {
  it("accepts keys that can reach the admin system endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ service: "AI Data Access Gateway", api_key_id: "key_admin" }),
    });

    await expect(validateAdminApiKey(fetchMock, "adg_valid_key")).resolves.toEqual({
      service: "AI Data Access Gateway",
      api_key_id: "key_admin",
    });

    expect(fetchMock).toHaveBeenCalledWith("/admin/system", {
      headers: {
        "Content-Type": "application/json",
        "X-ADG-API-Key": "adg_valid_key",
      },
    });
  });

  it("rejects keys that the admin endpoint marks as invalid", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => "Invalid API key",
    });

    await expect(validateAdminApiKey(fetchMock, "adg_invalid")).rejects.toThrow("Invalid API key");
  });
});
