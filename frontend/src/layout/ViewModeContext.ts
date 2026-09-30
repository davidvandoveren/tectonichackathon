import { createContext, useContext } from "react";

export type ViewModePreference = "auto" | "mobile" | "desktop";
export type ResolvedLayout = "mobile" | "desktop";

export interface ViewModeContextValue {
  /** The user's stored choice: "auto", "mobile" or "desktop". */
  preference: ViewModePreference;
  /** The actual layout to render, after resolving "auto" against the viewport. */
  resolved: ResolvedLayout;
  /** Whether the real viewport currently matches the desktop breakpoint (>= 900px). */
  isWideViewport: boolean;
  setPreference: (mode: ViewModePreference) => void;
}

export const ViewModeContext = createContext<ViewModeContextValue | null>(null);

export function useViewMode(): ViewModeContextValue {
  const context = useContext(ViewModeContext);
  if (!context) {
    throw new Error("useViewMode must be used within a ViewModeProvider");
  }
  return context;
}
