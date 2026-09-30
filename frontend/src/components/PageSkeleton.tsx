import { Skeleton } from "./Skeleton";
import styles from "./PageSkeleton.module.css";

export function PageSkeleton() {
  return (
    <div className={styles.wrapper} role="status" aria-live="polite">
      <span className="visually-hidden">Laden…</span>
      <Skeleton height={24} width="60%" />
      <Skeleton height={80} />
      <Skeleton height={80} />
    </div>
  );
}
