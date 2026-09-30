import { useEffect, useRef, type ReactNode } from "react";
import { ViewModeToggle } from "./ViewModeToggle";
import styles from "./PhoneFrame.module.css";

/** Real iPhone screen in CSS pixels plus the bezel around it. */
const DEVICE_WIDTH = 390 + 2 * 12;
const DEVICE_HEIGHT = 844 + 2 * 12;
const MARGIN = 32;

/**
 * Renders the mobile shell on a true 390x844 iPhone screen. The whole device is scaled down as
 * one piece when the browser window is smaller, so text, buttons and spacing keep exactly the
 * proportions of a real phone. Used when "Mobiel" is forced on a wide screen (demo machine).
 */
export function PhoneFrame({ children }: { children: ReactNode }) {
  const deviceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fit = () => {
      const scale = Math.min(
        1,
        (window.innerHeight - MARGIN) / DEVICE_HEIGHT,
        (window.innerWidth - MARGIN) / DEVICE_WIDTH,
      );
      deviceRef.current?.style.setProperty("--phone-scale", String(Math.max(scale, 0.4)));
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  return (
    <div className={styles.surround}>
      <div ref={deviceRef} className={styles.device}>
        <div className={styles.screen}>
          <div className={styles.viewport}>{children}</div>
        </div>
      </div>
      <ViewModeToggle variant="floating" />
    </div>
  );
}
