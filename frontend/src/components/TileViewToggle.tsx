import { GridIcon } from "./icons/GridIcon";
import { ListIcon } from "./icons/ListIcon";
import styles from "./TileViewToggle.module.css";

export type TileLayout = "grid" | "list";

interface TileViewToggleProps {
  value: TileLayout;
  onChange: (value: TileLayout) => void;
}

/** Grid/list segmented control for the account tiles on the Betalen page. */
export function TileViewToggle({ value, onChange }: TileViewToggleProps) {
  return (
    <div className={styles.group} role="group" aria-label="Weergave rekeningen">
      <button
        type="button"
        aria-pressed={value === "grid"}
        className={value === "grid" ? `${styles.option} ${styles.optionSelected}` : styles.option}
        onClick={() => onChange("grid")}
      >
        <GridIcon aria-hidden="true" />
        <span className="visually-hidden">Rasterweergave</span>
      </button>
      <button
        type="button"
        aria-pressed={value === "list"}
        className={value === "list" ? `${styles.option} ${styles.optionSelected}` : styles.option}
        onClick={() => onChange("list")}
      >
        <ListIcon aria-hidden="true" />
        <span className="visually-hidden">Lijstweergave</span>
      </button>
    </div>
  );
}
