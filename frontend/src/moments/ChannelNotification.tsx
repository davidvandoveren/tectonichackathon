import { useState } from "react";
import { INTERRUPTIVE, type FeedItem } from "./momentsApi";
import styles from "./ChannelNotification.module.css";

const HOW: Record<string, string> = { push: "Pushbericht", sms: "Sms", call: "Kate belt je" };

/**
 * A simulated phone notification for the one item Kate chose to interrupt the customer with.
 * The backend guarantees at most one interruptive item per feed; we only show that one.
 */
export function ChannelNotification({ items }: { items: FeedItem[] }) {
  const [closed, setClosed] = useState<string | null>(null);
  const item = items.find((candidate) => INTERRUPTIVE.has(candidate.channel));

  if (!item || closed === item.id) {
    return null;
  }

  return (
    <div className={styles.notification} role="status" aria-live="polite">
      <div className={styles.header}>
        <span className={styles.app}>Kate · KBC</span>
        <span className={styles.how}>{HOW[item.channel]} · nu</span>
        <button
          type="button"
          className={styles.close}
          aria-label="Melding sluiten"
          onClick={() => setClosed(item.id)}
        >
          ×
        </button>
      </div>
      <p className={styles.title}>{item.title}</p>
      <p className={styles.body}>{item.body}</p>
      <p className={styles.simulated}>Gesimuleerde melding voor de demo</p>
    </div>
  );
}
