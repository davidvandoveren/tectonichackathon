import { afterEach, describe, expect, it, vi } from "vitest";
import { readStoredViewMode, VIEW_MODE_STORAGE_KEY, writeStoredViewMode } from "./viewModeStorage";

describe("viewModeStorage", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("falls back to 'auto' when nothing is stored", () => {
    expect(readStoredViewMode()).toBe("auto");
  });

  it("round-trips a valid preference through localStorage", () => {
    writeStoredViewMode("desktop");
    expect(window.localStorage.getItem(VIEW_MODE_STORAGE_KEY)).toBe("desktop");
    expect(readStoredViewMode()).toBe("desktop");
  });

  it("falls back to 'auto' for a corrupted stored value", () => {
    window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, "giant-tv");
    expect(readStoredViewMode()).toBe("auto");
  });

  it("falls back to 'auto' when reading throws (e.g. blocked storage)", () => {
    vi.spyOn(window.localStorage.__proto__, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readStoredViewMode()).toBe("auto");
  });

  it("does not throw when writing fails (e.g. private mode quota)", () => {
    vi.spyOn(window.localStorage.__proto__, "setItem").mockImplementation(() => {
      throw new Error("quota exceeded");
    });
    expect(() => writeStoredViewMode("mobile")).not.toThrow();
  });
});
