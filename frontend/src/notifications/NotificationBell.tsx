import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { BellIcon } from "../components/icons/BellIcon";
import { getInbox, INTERRUPTIVE, markRead, type KateNotification } from "./notificationsApi";
import styles from "./NotificationBell.module.css";

const POLL_MS = 15_000;
const SEEN_KEY = "kate-toasted";
const HOW: Record<string, string> = { push: "Pushbericht", sms: "Sms", call: "Kate belt je" };

function loadSeen(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

function saveSeen(seen: Set<string>): void {
  try {
    sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seen].slice(-200)));
  } catch {
    // private mode: toasts may repeat after a reload, nothing else breaks
  }
}

interface NotificationBellProps {
  variant: "desktop" | "mobile";
}

/**
 * Kate's bell: unread badge, and a phone-style toast when she sends something new that is worth
 * interrupting for (push / sms / call). Kate decides and sends on the server; this only shows it.
 */
export function NotificationBell({ variant }: NotificationBellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [unread, setUnread] = useState(0);
  const [toast, setToast] = useState<KateNotification | null>(null);
  const seen = useRef<Set<string>>(loadSeen());
  const onHome = location.pathname === "/";

  useEffect(() => {
    let controller = new AbortController();
    const poll = () => {
      controller.abort();
      controller = new AbortController();
      getInbox(controller.signal)
        .then((inbox) => {
          setUnread(inbox.unread);
          // Home already shows the engine's own pop-up for moments; avoid a double.
          const fresh = inbox.items.find(
            (n) =>
              !n.read && INTERRUPTIVE.has(n.channel) && !seen.current.has(n.id) && !(onHome && n.source === "moment")
          );
          if (fresh) {
            seen.current.add(fresh.id);
            saveSeen(seen.current);
            setToast(fresh);
          }
        })
        .catch(() => undefined);
    };
    poll();
    const timer = window.setInterval(poll, POLL_MS);
    window.addEventListener("kate-notifications-refresh", poll);
    return () => {
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener("kate-notifications-refresh", poll);
    };
  }, [onHome]);

  function openToast(n: KateNotification) {
    setToast(null);
    void markRead(n.id).catch(() => undefined);
    navigate(n.cta_target.startsWith("/") ? n.cta_target : "/notifications");
  }

  const label = unread > 0 ? `Meldingen van Kate, ${unread} ongelezen` : "Meldingen van Kate";

  return (
    <>
      <button
        type="button"
        className={variant === "desktop" ? styles.desktopButton : styles.mobileButton}
        aria-label={label}
        onClick={() => navigate("/notifications")}
      >
        <span className={styles.iconWrap}>
          <BellIcon aria-hidden="true" />
          {unread > 0 && (
            <span className={styles.badge} aria-hidden="true">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </span>
        {variant === "desktop" && <span>Meldingen</span>}
      </button>

      {toast && (
        <div className={styles.toast} role="status" aria-live="polite">
          <div className={styles.toastHeader}>
            <span className={styles.app}>Kate · KBC</span>
            <span className={styles.how}>{HOW[toast.channel] ?? "Melding"} · nu</span>
            <button type="button" className={styles.close} aria-label="Melding sluiten" onClick={() => setToast(null)}>
              ×
            </button>
          </div>
          <button type="button" className={styles.toastBody} onClick={() => openToast(toast)}>
            <span className={styles.title}>{toast.title}</span>
            <span className={styles.body}>{toast.body}</span>
          </button>
        </div>
      )}
    </>
  );
}
