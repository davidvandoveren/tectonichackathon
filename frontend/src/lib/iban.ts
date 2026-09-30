/** IBAN helpers: normalization, display formatting and mod-97 checksum validation (ISO 7064). */

export function normalizeIban(iban: string): string {
  return iban.replace(/\s+/g, "").toUpperCase();
}

/** Formats an IBAN for display in groups of four characters, e.g. "BE68 5390 0754 7034". */
export function formatIban(iban: string): string {
  const normalized = normalizeIban(iban);
  return (normalized.match(/.{1,4}/g) ?? [normalized]).join(" ");
}

/**
 * Validates the IBAN structure and mod-97 checksum. Spaces are allowed in the input.
 * Length bounds (5-34) follow the general ISO 13616 IBAN format.
 */
export function isValidIban(iban: string): boolean {
  const normalized = normalizeIban(iban);

  if (normalized.length < 5 || normalized.length > 34) {
    return false;
  }
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]+$/.test(normalized)) {
    return false;
  }

  const rearranged = normalized.slice(4) + normalized.slice(0, 4);
  const numeric = rearranged.replace(/[A-Z]/g, (letter) => String(letter.charCodeAt(0) - 55));

  let remainder = 0;
  for (let i = 0; i < numeric.length; i += 7) {
    remainder = Number(`${remainder}${numeric.slice(i, i + 7)}`) % 97;
  }

  return remainder === 1;
}
