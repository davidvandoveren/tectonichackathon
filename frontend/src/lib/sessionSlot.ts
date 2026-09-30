/**
 * Demo session slot. The /duo page embeds the app twice (two phones side by side); each copy
 * opens with `?slot=a` or `?slot=b` and sends it as `X-Session-Slot`, so the server keeps two
 * separate HttpOnly session cookies and each phone can be logged in as a different persona.
 *
 * The slot itself is not a secret (the cookie is); it is remembered per browser tab in
 * sessionStorage so it survives navigation inside the embedded app.
 */
export type SessionSlot = "a" | "b";

const STORAGE_KEY = "demo.sessionSlot";

function isSlot(value: string | null): value is SessionSlot {
  return value === "a" || value === "b";
}

function readSlot(): SessionSlot | null {
  if (typeof window === "undefined") return null;
  const fromUrl = new URLSearchParams(window.location.search).get("slot");
  try {
    if (isSlot(fromUrl)) {
      window.sessionStorage.setItem(STORAGE_KEY, fromUrl);
      return fromUrl;
    }
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    return isSlot(stored) ? stored : null;
  } catch {
    return isSlot(fromUrl) ? fromUrl : null;
  }
}

/** Resolved once at startup: the slot never changes while the app runs. */
export const sessionSlot: SessionSlot | null = readSlot();
