import styles from "./Wordmark.module.css";

export function Wordmark() {
  return (
    <p className={styles.wordmark}>
      KBC Mobile <span className={styles.badge}>PoC</span>
    </p>
  );
}
