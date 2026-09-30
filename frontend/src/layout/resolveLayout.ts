import type { ResolvedLayout, ViewModePreference } from "./ViewModeContext";

/**
 * Pure resolution of the effective layout: an explicit "mobile"/"desktop"
 * preference always wins; "auto" resolves from the actual viewport width
 * (>= 900px matches the `(min-width: 900px)` media query considered "desktop").
 */
export function resolveLayout(preference: ViewModePreference, isWideViewport: boolean): ResolvedLayout {
  if (preference === "mobile") {
    return "mobile";
  }
  if (preference === "desktop") {
    return "desktop";
  }
  return isWideViewport ? "desktop" : "mobile";
}
