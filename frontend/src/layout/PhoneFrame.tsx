import type { ReactNode } from "react";
import { ViewModeToggle } from "./ViewModeToggle";
import styles from "./PhoneFrame.module.css";

/**
 * Renders the mobile shell inside a centered 390x844 phone frame. Used when
 * the layout preference is forced to "mobile" while the real viewport is
 * wide (desktop demo machine), so the app still reads as a phone screen.
 */
export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className={styles.surround}>
      <div className={styles.device}>
        <div className={styles.screen}>{children}</div>
      </div>
      <ViewModeToggle variant="floating" />
    </div>
  );
}
