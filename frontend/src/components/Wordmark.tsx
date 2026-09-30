import styles from "./Wordmark.module.css";

interface WordmarkProps {
  /** Smaller size, for tight spaces like the mobile top bar. */
  compact?: boolean;
  /** "light" renders white text, for use on a navy background. */
  tone?: "navy" | "light";
}

export function Wordmark({ compact = false, tone = "navy" }: WordmarkProps) {
  const classNames = [
    styles.wordmark,
    compact ? styles.compact : "",
    tone === "light" ? styles.light : "",
  ]
    .filter(Boolean)
    .join(" ");
  return <span className={classNames}>KBC</span>;
}
