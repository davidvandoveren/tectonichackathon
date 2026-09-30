import { useEffect, useId, useState } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Skeleton } from "../components/Skeleton";
import { ChevronDownIcon } from "../components/icons/ChevronDownIcon";
import { formatDateLong } from "../lib/dates";
import {
  getInbox,
  markAllRead,
  markRead,
  refreshNotifications,
  type Inbox,
  type KateNotification,
} from "./notificationsApi";
import styles from "./NotificationsPage.module.css";

const CHANNEL_LABEL: Record<string, string> = {
  feed: "In de app",
  push: "Pushbericht",
  sms: "Sms",
  call: "Kate belde",
};
const SOURCE_LABEL: Record<string, string> = {
  moment: "Kate merkte op",
  family: "Familiekring",
  invest: "Beleggen",
};

export function NotificationsPage() {
  const [inbox, setInbox] = useState<Inbox | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load(signal?: AbortSignal) {
    getInbox(signal)
      .then((data) => {
        setInbox(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (signal?.aborted) return;
        setError(err instanceof ApiError ? err.detail : "Kan je meldingen niet laden.");
      });
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  async function readAll() {
    await markAllRead().catch(() => undefined);
    refreshNotifications();
    load();
  }

  async function read(n: KateNotification) {
    if (n.read) return;
    await markRead(n.id).catch(() => undefined);
    refreshNotifications();
    setInbox((current) =>
      current && {
        unread: Math.max(0, current.unread - 1),
        items: current.items.map((item) => (item.id === n.id ? { ...item, read: true } : item)),
      }
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader title="Meldingen van Kate" showBack />
      <div className={styles.content}>
        <p className={styles.intro}>
          Kate kijkt zelf mee en stuurt je alleen iets als het de moeite is, via het kanaal dat past bij hoe dringend
          het is. Bij elke melding staat waarom.
        </p>
        {!inbox && !error && (
          <>
            <Skeleton height={90} />
            <Skeleton height={90} />
          </>
        )}
        {error && <ErrorState message={error} onRetry={() => load()} />}
        {inbox && inbox.items.length === 0 && <EmptyState message="Nog geen meldingen. Kate laat van zich horen." />}
        {inbox && inbox.items.length > 0 && (
          <>
            <div className={styles.toolbar}>
              <span>{inbox.unread > 0 ? `${inbox.unread} ongelezen` : "Alles gelezen"}</span>
              {inbox.unread > 0 && (
                <button type="button" className={styles.linkButton} onClick={() => void readAll()}>
                  Alles gelezen
                </button>
              )}
            </div>
            <ul className={styles.list}>
              {inbox.items.map((n) => (
                <NotificationItem key={n.id} notification={n} onRead={() => void read(n)} />
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

function NotificationItem({ notification: n, onRead }: { notification: KateNotification; onRead: () => void }) {
  const [open, setOpen] = useState(false);
  const reasonId = useId();
  return (
    <li className={`${styles.item} ${n.read ? styles.read : ""}`}>
      <div className={styles.meta}>
        {!n.read && <span className={styles.unreadDot} aria-label="Ongelezen" />}
        <span>{SOURCE_LABEL[n.source] ?? "Kate"}</span>
        <span>·</span>
        <span>{CHANNEL_LABEL[n.channel] ?? n.channel}</span>
        <span>·</span>
        <span>{formatDateLong(n.sent_on)}</span>
      </div>
      <p className={styles.title}>{n.title}</p>
      <p className={styles.body}>{n.body}</p>
      <div className={styles.actions}>
        {n.cta_target.startsWith("/") && n.cta_label && (
          <Link to={n.cta_target} className={styles.cta} onClick={onRead}>
            {n.cta_label}
          </Link>
        )}
        {!n.read && (
          <button type="button" className={styles.linkButton} onClick={onRead}>
            Gelezen
          </button>
        )}
      </div>
      <button
        type="button"
        className={styles.reasonToggle}
        aria-expanded={open}
        aria-controls={reasonId}
        onClick={() => setOpen((v) => !v)}
      >
        Waarom kreeg ik dit?
        <ChevronDownIcon className={open ? styles.chevronOpen : styles.chevron} aria-hidden="true" />
      </button>
      {open && (
        <p id={reasonId} className={styles.reason}>
          {n.reason}
        </p>
      )}
    </li>
  );
}
