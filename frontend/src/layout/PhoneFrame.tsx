import { useEffect, useState, type ReactNode } from "react";
import { ViewModeToggle } from "./ViewModeToggle";
import styles from "./PhoneFrame.module.css";

function useClock(): string {
  const format = () => new Date().toLocaleTimeString("nl-BE", { hour: "2-digit", minute: "2-digit" });
  const [time, setTime] = useState(format);
  useEffect(() => {
    const timer = window.setInterval(() => setTime(format()), 15_000);
    return () => window.clearInterval(timer);
  }, []);
  return time;
}

/**
 * Renders the mobile shell inside a phone (iPhone proportions, 390x844) with a status bar, Dynamic
 * Island, side buttons and home indicator. Used when "mobile" is forced on a wide screen (demo on a
 * laptop). The status bar is chrome: the app lives in the area below it and never scrolls as a
 * whole, so its top bar and tab bar stay where a real app keeps them.
 */
export function PhoneFrame({ children }: { children: ReactNode }) {
  const time = useClock();
  return (
    <div className={styles.surround}>
      <div className={styles.device}>
        <span className={`${styles.sideButton} ${styles.action}`} aria-hidden="true" />
        <span className={`${styles.sideButton} ${styles.volumeUp}`} aria-hidden="true" />
        <span className={`${styles.sideButton} ${styles.volumeDown}`} aria-hidden="true" />
        <span className={`${styles.sideButton} ${styles.power}`} aria-hidden="true" />
        <div className={styles.screen}>
          <div className={styles.statusBar} aria-hidden="true">
            <span className={styles.time}>{time}</span>
            <span className={styles.island} />
            <span className={styles.indicators}>
              <SignalIcon />
              <WifiIcon />
              <BatteryIcon />
            </span>
          </div>
          <div className={styles.viewport}>{children}</div>
          <span className={styles.homeIndicator} aria-hidden="true" />
        </div>
      </div>
      <ViewModeToggle variant="floating" />
    </div>
  );
}

function SignalIcon() {
  return (
    <svg width="18" height="12" viewBox="0 0 18 12" fill="currentColor">
      <rect x="0" y="8" width="3" height="4" rx="1" />
      <rect x="5" y="5.5" width="3" height="6.5" rx="1" />
      <rect x="10" y="3" width="3" height="9" rx="1" />
      <rect x="15" y="0" width="3" height="12" rx="1" />
    </svg>
  );
}

function WifiIcon() {
  return (
    <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor">
      <path d="M8 2.2c2.4 0 4.6.9 6.2 2.4l1.3-1.4A10.9 10.9 0 0 0 8 .3 10.9 10.9 0 0 0 .5 3.2l1.3 1.4A9 9 0 0 1 8 2.2Z" />
      <path d="M8 5.8c1.5 0 2.8.5 3.8 1.4l1.3-1.4A7.4 7.4 0 0 0 8 3.9a7.4 7.4 0 0 0-5.1 1.9l1.3 1.4c1-.9 2.3-1.4 3.8-1.4Z" />
      <path d="M8 9.3c.6 0 1.1.2 1.5.6L8 11.6 6.5 9.9c.4-.4.9-.6 1.5-.6Z" />
    </svg>
  );
}

function BatteryIcon() {
  return (
    <svg width="27" height="13" viewBox="0 0 27 13">
      <rect x="0.5" y="0.5" width="23" height="12" rx="3.5" fill="none" stroke="currentColor" opacity="0.4" />
      <rect x="2" y="2" width="17" height="9" rx="2" fill="currentColor" />
      <path d="M25 4.5v4c.8-.3 1.3-1.1 1.3-2s-.5-1.7-1.3-2Z" fill="currentColor" opacity="0.4" />
    </svg>
  );
}
