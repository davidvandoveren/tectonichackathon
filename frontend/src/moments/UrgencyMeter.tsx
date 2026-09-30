import { bandOf } from "./momentsApi";
import styles from "./UrgencyMeter.module.css";

const BAND_LABEL = { risk: "Dringend", obligation: "Belangrijk", opportunity: "Kans" } as const;

const CHANNEL_LABEL: Record<string, string> = {
  push: "Pushbericht",
  sms: "Sms",
  call: "Kate belt",
};

interface UrgencyMeterProps {
  urgency?: number;
  channel?: string;
}

/** How urgent Kate finds this, and how she chose to reach the customer. */
export function UrgencyMeter({ urgency, channel }: UrgencyMeterProps) {
  if (urgency === undefined || urgency === null) {
    return null;
  }
  const band = bandOf(urgency);
  const channelLabel = channel ? CHANNEL_LABEL[channel] : undefined;

  return (
    <div className={styles.meter}>
      <div
        className={styles.track}
        role="meter"
        aria-label="Urgentie"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={urgency}
        aria-valuetext={`${BAND_LABEL[band]}, ${urgency} op 100`}
      >
        <span className={`${styles.fill} ${styles[band]}`} style={{ width: `${urgency}%` }} />
      </div>
      <span className={`${styles.label} ${styles[`${band}Text`]}`}>
        {BAND_LABEL[band]} · {urgency}
      </span>
      {channelLabel && <span className={styles.channel}>{channelLabel}</span>}
    </div>
  );
}
