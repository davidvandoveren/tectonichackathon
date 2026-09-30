import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";

describe("apiClient", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends JSON on a POST without payload (logout used to get a 415)", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    await apiClient.post("/auth/logout");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(init.body).toBe("{}");
  });

  it("sends no body on a GET", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("[]", { headers: { "content-type": "application/json" } }));
    await apiClient.get("/accounts");
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBeUndefined();
  });
});
