import { describe, expect, it } from "vitest";
import { formatMoney, isValidAmount, splitMoney, sumMoney, toAmountString } from "./money";

describe("formatMoney", () => {
  it("formats a positive euro amount in nl-BE", () => {
    const formatted = formatMoney("1234.50", "EUR");
    expect(formatted).toContain("1.234,50");
    expect(formatted).toContain("€");
  });

  it("formats a negative amount", () => {
    expect(formatMoney("-42.17", "EUR")).toContain("42,17");
  });
});

describe("isValidAmount", () => {
  it("accepts a valid amount", () => {
    expect(isValidAmount("25.00")).toBe(true);
  });

  it("accepts a comma decimal separator", () => {
    expect(isValidAmount("25,5")).toBe(true);
  });

  it("rejects zero", () => {
    expect(isValidAmount("0")).toBe(false);
  });

  it("rejects negative amounts", () => {
    expect(isValidAmount("-5")).toBe(false);
  });

  it("rejects more than two decimals", () => {
    expect(isValidAmount("25.123")).toBe(false);
  });

  it("rejects an amount above the maximum", () => {
    expect(isValidAmount("10000.01")).toBe(false);
  });

  it("accepts the maximum amount", () => {
    expect(isValidAmount("10000")).toBe(true);
  });
});

describe("toAmountString", () => {
  it("pads a single decimal to two digits", () => {
    expect(toAmountString("25.5")).toBe("25.50");
  });

  it("adds decimals when missing", () => {
    expect(toAmountString("25")).toBe("25.00");
  });

  it("normalizes a comma decimal separator", () => {
    expect(toAmountString("25,5")).toBe("25.50");
  });
});

describe("sumMoney", () => {
  it("sums amounts without floating point drift", () => {
    expect(sumMoney(["0.10", "0.20"])).toBe("0.30");
  });

  it("handles negative amounts", () => {
    expect(sumMoney(["100.00", "-42.17"])).toBe("57.83");
  });

  it("returns 0.00 for an empty list", () => {
    expect(sumMoney([])).toBe("0.00");
  });
});

describe("splitMoney", () => {
  it("splits a large amount into grouped integer and decimal parts", () => {
    expect(splitMoney("13023.97", "EUR")).toEqual({
      sign: "",
      integer: "13 023",
      decimals: "97",
      currency: "EUR",
    });
  });

  it("marks negative amounts with a sign and drops it from the digits", () => {
    expect(splitMoney("-42.17", "EUR")).toEqual({
      sign: "-",
      integer: "42",
      decimals: "17",
      currency: "EUR",
    });
  });

  it("pads a whole amount to two decimals", () => {
    expect(splitMoney("25", "EUR")).toEqual({
      sign: "",
      integer: "25",
      decimals: "00",
      currency: "EUR",
    });
  });

  it("formats zero without a sign", () => {
    expect(splitMoney("0.00", "EUR")).toEqual({
      sign: "",
      integer: "0",
      decimals: "00",
      currency: "EUR",
    });
  });
});
