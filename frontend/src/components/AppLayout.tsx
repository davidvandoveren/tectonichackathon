import { Outlet } from "react-router";
import type { ReactNode } from "react";
import { useViewMode } from "../layout/ViewModeContext";
import { DesktopShell } from "../layout/DesktopShell";
import { MobileShell } from "../layout/MobileShell";
import { PhoneFrame } from "../layout/PhoneFrame";
import { KateChat } from "../kate/KateChat";

/**
 * Picks the desktop or mobile chrome around the routed page, based on the
 * resolved view mode. When "mobile" is explicitly forced on a wide viewport
 * (demo scenario), the mobile shell is rendered inside a phone frame.
 *
 * This component is the single place global overlays are mounted (like
 * `<KateChat />`), alongside the shell, so they render above the routed page
 * regardless of layout. On desktop Kate opens from the header button instead
 * of her own floating launcher.
 */
export function AppLayout() {
  const { resolved, preference, isWideViewport } = useViewMode();

  let shell: ReactNode;
  if (resolved === "desktop") {
    shell = (
      <DesktopShell>
        <Outlet />
      </DesktopShell>
    );
  } else {
    const framed = preference === "mobile" && isWideViewport;
    const mobileShell = (
      <MobileShell>
        <Outlet />
        <KateChat hideLauncher />
      </MobileShell>
    );
    return framed ? <PhoneFrame>{mobileShell}</PhoneFrame> : mobileShell;
  }

  return (
    <>
      {shell}
      <KateChat hideLauncher />
    </>
  );
}
