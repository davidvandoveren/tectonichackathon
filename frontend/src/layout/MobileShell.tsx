import type { ReactNode } from "react";
import { Wordmark } from "../components/Wordmark";
import { BellIcon } from "../components/icons/BellIcon";
import { TabBar } from "../components/TabBar";
import { ViewModeToggle } from "./ViewModeToggle";
import styles from "./MobileShell.module.css";

/** KBC Mobile-style shell: compact top bar, full-width content, bottom tab bar. */
export function MobileShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <Wordmark compact />
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
      </header>
      <main className={styles.content}>{children}</main>
      <TabBar />
      <ViewModeToggle variant="floating" compact />
    </div>
  );
}
