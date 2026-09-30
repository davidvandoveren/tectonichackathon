/**
 * Persistence for the mobile/desktop layout preference. This is a UI
 * preference only (no personal data), so every read/write is wrapped in
 * try/catch and falls back to "auto" if localStorage is unavailable
 * (private browsing, blocked storage, etc.).
 */
import type { ViewModePreference } from "./ViewModeContext";

export const VIEW_MODE_STORAGE_KEY = "ui.viewMode";

const VALID_PREFERENCES: readonly ViewModePreference[] = ["auto", "mobile", "desktop"];

function isViewModePreference(value: string | null): value is ViewModePreference {
  return value !== null && (VALID_PREFERENCES as readonly string[]).includes(value);
}

export function readStoredViewMode(): ViewModePreference {
  try {
    const stored = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return isViewModePreference(stored) ? stored : "auto";
  } catch {
    return "auto";
  }
}

export function writeStoredViewMode(mode: ViewModePreference): void {
  try {
    window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // Preference just won't persist across reloads; not a functional error.
  }
}
