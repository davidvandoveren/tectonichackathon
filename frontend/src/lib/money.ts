/**
 * Money helpers. Amounts are always decimal strings ("1234.50"), per the API contract.
 * Summation uses integer cents (BigInt) instead of float arithmetic to avoid rounding drift.
 */

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

/** Normalizes user input: trims whitespace and accepts a comma as decimal separator. */
export function normalizeAmountInput(raw: string): string {
  return raw.trim().replace(",", ".");
}

/** Validates amount > 0, max 2 decimals, and an inclusive maximum (default 10000, per the transfer contract). */
export function isValidAmount(raw: string, max = 10000): boolean {
  const normalized = normalizeAmountInput(raw);
  if (!MONEY_PATTERN.test(normalized)) {
    return false;
  }
  const value = Number(normalized);
  return value > 0 && value <= max;
}

/** Converts validated user input into a canonical 2-decimal amount string, e.g. "25" -> "25.00". */
export function toAmountString(raw: string): string {
  const normalized = normalizeAmountInput(raw);
  const [integerPart, decimalPart = ""] = normalized.split(".");
  return `${integerPart}.${decimalPart.padEnd(2, "0").slice(0, 2)}`;
}

/** Formats a decimal amount string as localized currency text. Never used for arithmetic. */
export function formatMoney(amount: string, currency: string): string {
  return new Intl.NumberFormat("nl-BE", { style: "currency", currency }).format(Number(amount));
}

function toCents(amount: string): bigint {
  const trimmed = amount.trim();
  const isNegative = trimmed.startsWith("-");
  const unsigned = isNegative ? trimmed.slice(1) : trimmed;
  const [integerPart, decimalPart = ""] = unsigned.split(".");
  const cents = BigInt(integerPart || "0") * 100n + BigInt(decimalPart.padEnd(2, "0").slice(0, 2) || "0");
  return isNegative ? -cents : cents;
}

function fromCents(cents: bigint): string {
  const isNegative = cents < 0n;
  const absolute = isNegative ? -cents : cents;
  const integerPart = absolute / 100n;
  const decimalPart = (absolute % 100n).toString().padStart(2, "0");
  return `${isNegative ? "-" : ""}${integerPart}.${decimalPart}`;
}

/** Sums decimal amount strings exactly, using integer cents instead of floating point math. */
export function sumMoney(amounts: string[]): string {
  const totalCents = amounts.reduce((total, amount) => total + toCents(amount), 0n);
  return fromCents(totalCents);
}

export interface MoneyParts {
  /** "-" for negative amounts, "" otherwise. */
  sign: string;
  /** Thousands-grouped integer part (space-separated, e.g. "1 234"). */
  integer: string;
  /** Two-digit decimal part, e.g. "50". */
  decimals: string;
  currency: string;
}

/** Groups a plain digit string into thousands with a space, e.g. "13023" -> "13 023". */
function groupThousands(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/**
 * Splits a decimal amount string into display parts for the KBC-style tile
 * amount ("13 023,97 EUR": integer part large, decimals + currency small).
 * Never does float arithmetic — grouping is done on the integer-cents string.
 */
export function splitMoney(amount: string, currency: string): MoneyParts {
  const cents = toCents(amount);
  const isNegative = cents < 0n;
  const absolute = isNegative ? -cents : cents;
  const integerDigits = (absolute / 100n).toString();
  const decimals = (absolute % 100n).toString().padStart(2, "0");
  return { sign: isNegative ? "-" : "", integer: groupThousands(integerDigits), decimals, currency };
}
