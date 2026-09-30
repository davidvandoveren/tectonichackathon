import { describe, expect, it } from "vitest";
import { resolveLayout } from "./resolveLayout";

describe("resolveLayout", () => {
  it("resolves to mobile when forced, regardless of viewport", () => {
    expect(resolveLayout("mobile", true)).toBe("mobile");
    expect(resolveLayout("mobile", false)).toBe("mobile");
  });

  it("resolves to desktop when forced, regardless of viewport", () => {
    expect(resolveLayout("desktop", true)).toBe("desktop");
    expect(resolveLayout("desktop", false)).toBe("desktop");
  });

  it("resolves 'auto' to desktop on a wide viewport", () => {
    expect(resolveLayout("auto", true)).toBe("desktop");
  });

  it("resolves 'auto' to mobile on a narrow viewport", () => {
    expect(resolveLayout("auto", false)).toBe("mobile");
  });
});
