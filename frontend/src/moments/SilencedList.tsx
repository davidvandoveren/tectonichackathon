import { useId, useState } from "react";
import { ChevronDownIcon } from "../components/icons/ChevronDownIcon";
import type { Silence } from "./momentsApi";
import styles from "./SilencedList.module.css";

/** What Kate noticed and deliberately kept to herself, each with its reason. */
export function SilencedList({ silenced }: { silenced: Silence[] }) {
  const [open, setOpen] = useState(false);
  const listId = useId();

  if (silenced.length === 0) {
    return null;
  }

  return (
    <section className={styles.section} aria-label="Bewust niet gezegd">
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((value) => !value)}
      >
        <span>
          Bewust niet gezegd <span className={styles.count}>{silenced.length}</span>
        </span>
        <ChevronDownIcon className={open ? styles.chevronOpen : styles.chevron} aria-hidden="true" />
      </button>
      {open && (
        <ul id={listId} className={styles.list}>
          {silenced.map((entry) => (
            <li key={`${entry.moment}-${entry.reason_code}`} className={styles.item}>
              {entry.reason}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
