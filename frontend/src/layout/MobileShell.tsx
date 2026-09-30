import { useEffect, useRef, type ReactNode } from "react";
import { useLocation } from "react-router";
import { Wordmark } from "../components/Wordmark";
import { BellIcon } from "../components/icons/BellIcon";
import { TabBar } from "../components/TabBar";
import { SparkleIcon } from "../kate/icons";
import { openKate } from "../kate/openKate";
import styles from "./MobileShell.module.css";

/**
 * KBC Mobile-style shell, laid out like a native app: the top bar and the tab bar stay put and only
 * the content in between scrolls. That keeps the tab bar at the bottom both on a real phone and
 * inside the demo phone frame (where the page itself never scrolls).
 */
export function MobileShell({ children }: { children: ReactNode }) {
  const content = useRef<HTMLElement | null>(null);
  const { pathname } = useLocation();

  // The content area is the scroll container, so a new screen must start at the top.
  useEffect(() => {
    content.current?.scrollTo?.({ top: 0 });
  }, [pathname]);

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <Wordmark compact />
        <div className={styles.actions}>
          <button type="button" className={styles.kateButton} onClick={openKate} aria-label="Open Kate">
            <SparkleIcon width={16} height={16} aria-hidden="true" />
            <span>Kate</span>
          </button>
          <button
            type="button"
            className={styles.iconButton}
            aria-disabled="true"
            title="Binnenkort"
            aria-label="Acties"
          >
            <BellIcon aria-hidden="true" />
            <span className={styles.dot} aria-hidden="true" />
          </button>
        </div>
      </header>
      <main ref={content} className={styles.content}>
        {children}
      </main>
      <TabBar />
    </div>
  );
}
