import type { ReactNode } from "react";
import { Link } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { Wordmark } from "../components/Wordmark";
import { BellIcon } from "../components/icons/BellIcon";
import { TabBar } from "../components/TabBar";
import { SparkleIcon } from "../kate/icons";
import { openKate } from "../kate/openKate";
import styles from "./MobileShell.module.css";


function initials(firstName?: string, lastName?: string): string {
  return `${firstName?.[0] ?? ""}${lastName?.[0] ?? ""}`.toUpperCase() || "?";
}

/**
 * KBC Mobile-style shell. The top bar and tab bar are part of the layout (not position: fixed),
 * and only the content in between scrolls, so it behaves the same on a real phone and in the
 * desktop phone frame.
 */
export function MobileShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <Link to="/profile" className={styles.avatar} aria-label="Mijn profiel">
          {initials(user?.first_name, user?.last_name)}
        </Link>
        <Wordmark compact />
        <div className={styles.actions}>
          <button type="button" className={styles.kate} onClick={openKate} aria-label="Vraag het Kate">
            <SparkleIcon width={18} height={18} aria-hidden="true" />
            <span>Kate</span>
          </button>
          <button type="button" className={styles.iconButton} aria-disabled="true" title="Binnenkort" aria-label="Meldingen">
            <BellIcon aria-hidden="true" />
            <span className={styles.dot} aria-hidden="true" />
          </button>
        </div>
      </header>
      <main className={styles.content}>{children}</main>
      <TabBar />
    </div>
  );
}
