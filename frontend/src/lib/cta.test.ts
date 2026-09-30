import { describe, expect, it } from "vitest";
import { isSafeInternalPath } from "./cta";

describe("isSafeInternalPath", () => {
  it("accepts root-relative app paths", () => {
    expect(isSafeInternalPath("/transfer?to_name=Lucas&amount=25.00")).toBe(true);
    expect(isSafeInternalPath("/subscriptions")).toBe(true);
  });

  it("rejects external, protocol-relative and scheme URLs", () => {
    expect(isSafeInternalPath("https://evil.example")).toBe(false);
    expect(isSafeInternalPath("//evil.example")).toBe(false);
    expect(isSafeInternalPath("javascript:alert(1)")).toBe(false);
  });

  it("rejects backslash and control-character tricks browsers turn into '//'", () => {
    expect(isSafeInternalPath("/\\evil.example")).toBe(false);
    expect(isSafeInternalPath("/\t/evil.example")).toBe(false);
    expect(isSafeInternalPath("/\n/evil.example")).toBe(false);
  });
});
