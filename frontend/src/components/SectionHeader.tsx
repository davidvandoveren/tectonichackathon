import { PlusCircleIcon } from "./icons/PlusCircleIcon";
import styles from "./SectionHeader.module.css";

interface SectionHeaderProps {
  id: string;
  title: string;
}

/** "Zichtrekeningen" / "Spaarrekeningen" / ... section title with a decorative "+ Nieuw" link. */
export function SectionHeader({ id, title }: SectionHeaderProps) {
  return (
    <div className={styles.row}>
      <h2 id={id} className={styles.title}>
        {title}
      </h2>
      <span className={styles.newLink} aria-disabled="true" title="Binnenkort">
        <PlusCircleIcon aria-hidden="true" className={styles.plus} />
        <span>Nieuw</span>
      </span>
    </div>
  );
}
