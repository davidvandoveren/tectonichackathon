import { describe, expect, it } from "vitest";
import { formatIban, isValidIban, normalizeIban } from "./iban";

describe("normalizeIban", () => {
  it("removes spaces and uppercases", () => {
    expect(normalizeIban(" be68 5390 0754 7034 ")).toBe("BE68539007547034");
  });
});

describe("isValidIban", () => {
  it("accepts a valid Belgian IBAN with spaces", () => {
    expect(isValidIban("BE68 5390 0754 7034")).toBe(true);
  });

  it("accepts a valid IBAN without spaces", () => {
    expect(isValidIban("BE71096123456769")).toBe(true);
  });

  it("rejects an IBAN with a bad checksum", () => {
    expect(isValidIban("BE68 5390 0754 7035")).toBe(false);
  });

  it("rejects an empty string", () => {
    expect(isValidIban("")).toBe(false);
  });

  it("rejects an IBAN that is too short", () => {
    expect(isValidIban("BE68")).toBe(false);
  });

  it("rejects an IBAN with an invalid country/check-digit prefix", () => {
    expect(isValidIban("1234567890123456")).toBe(false);
  });
});

describe("formatIban", () => {
  it("groups the IBAN into blocks of four", () => {
    expect(formatIban("BE68539007547034")).toBe("BE68 5390 0754 7034");
  });

  it("normalizes lowercase and extra spacing before grouping", () => {
    expect(formatIban("be68  5390 0754 7034")).toBe("BE68 5390 0754 7034");
  });
});
