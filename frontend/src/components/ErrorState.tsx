import { Button } from "./Button";
import styles from "./ErrorState.module.css";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className={styles.wrapper} role="alert" aria-live="assertive">
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <Button type="button" variant="secondary" onClick={onRetry}>
          Opnieuw proberen
        </Button>
      )}
    </div>
  );
}
