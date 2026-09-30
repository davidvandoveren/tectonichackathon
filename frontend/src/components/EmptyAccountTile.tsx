import { PlusCircleIcon } from "./icons/PlusCircleIcon";
import styles from "./EmptyAccountTile.module.css";

interface EmptyAccountTileProps {
  message: string;
}

/** Outlined placeholder tile for an account-type section with no accounts (e.g. no credit card). */
export function EmptyAccountTile({ message }: EmptyAccountTileProps) {
  return (
    <div className={styles.tile}>
      <PlusCircleIcon aria-hidden="true" className={styles.icon} />
      <span>{message}</span>
    </div>
  );
}
