import { Outlet, useLocation } from "react-router";
import type { ReactNode } from "react";
import { useViewMode } from "../layout/ViewModeContext";
import { DesktopShell } from "../layout/DesktopShell";
import { MobileShell } from "../layout/MobileShell";
import { PhoneFrame } from "../layout/PhoneFrame";
import { KateChat } from "../kate/KateChat";
import { PageErrorBoundary } from "./PageErrorBoundary";

/**
 * Picks the desktop or mobile chrome around the routed page, based on the
 * resolved view mode. When "mobile" is explicitly forced on a wide viewport
 * (demo scenario), the mobile shell is rendered inside a phone frame.
 *
 * This component is the single place global overlays are mounted (like
 * `<KateChat />`), alongside the shell, so they render above the routed page
 * regardless of layout. Kate opens from a button in the shell's header (desktop
 * and mobile), never from a launcher floating over the content.
 */
export function AppLayout() {
  const { resolved, preference, isWideViewport } = useViewMode();
  const { pathname } = useLocation();
  // One boundary per screen: a crash stays inside that screen and clears when you navigate away.
  const page = (
    <PageErrorBoundary key={pathname}>
      <Outlet />
    </PageErrorBoundary>
  );

  let shell: ReactNode;
  if (resolved === "desktop") {
    shell = (
      <DesktopShell>{page}</DesktopShell>
    );
  } else {
    const framed = preference === "mobile" && isWideViewport;
    // Kate opens from the Kate button in the mobile top bar, so no floating launcher over content.
    const mobileShell = (
      <>
        <MobileShell>{page}</MobileShell>
        <KateChat hideLauncher />
      </>
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
