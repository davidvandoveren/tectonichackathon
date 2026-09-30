import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ViewModeContext, type ViewModePreference } from "./ViewModeContext";
import { readStoredViewMode, writeStoredViewMode } from "./viewModeStorage";
import { resolveLayout } from "./resolveLayout";
import { sessionSlot } from "../lib/sessionSlot";

export const DESKTOP_MEDIA_QUERY = "(min-width: 900px)";

function getIsWideViewport(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia(DESKTOP_MEDIA_QUERY).matches;
}

export function ViewModeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ViewModePreference>(() => readStoredViewMode());
  const [isWideViewport, setIsWideViewport] = useState<boolean>(() => getIsWideViewport());

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mediaQueryList = window.matchMedia(DESKTOP_MEDIA_QUERY);
    const handleChange = (event: MediaQueryListEvent) => setIsWideViewport(event.matches);
    mediaQueryList.addEventListener("change", handleChange);
    return () => mediaQueryList.removeEventListener("change", handleChange);
  }, []);

  const setPreference = useCallback((mode: ViewModePreference) => {
    setPreferenceState(mode);
    writeStoredViewMode(mode);
  }, []);

  // A phone embedded in the /duo page is always a plain phone: mobile layout, no extra frame.
  const embedded = sessionSlot !== null;
  const resolved = useMemo(
    () => (embedded ? "mobile" : resolveLayout(preference, isWideViewport)),
    [embedded, preference, isWideViewport]
  );

  const value = useMemo(
    () => ({ preference, resolved, isWideViewport: embedded ? false : isWideViewport, setPreference }),
    [embedded, preference, resolved, isWideViewport, setPreference]
  );

  return <ViewModeContext.Provider value={value}>{children}</ViewModeContext.Provider>;
}
