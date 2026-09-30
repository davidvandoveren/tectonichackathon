import { useRef, type ComponentType, type KeyboardEvent, type SVGProps } from "react";
import { useViewMode } from "./ViewModeContext";
import type { ViewModePreference } from "./ViewModeContext";
import { PhoneIcon } from "../components/icons/PhoneIcon";
import { MonitorIcon } from "../components/icons/MonitorIcon";
import styles from "./ViewModeToggle.module.css";

interface ViewModeOption {
  value: ViewModePreference;
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>> | null;
}

const OPTIONS: ViewModeOption[] = [
  { value: "mobile", label: "Mobiel", Icon: PhoneIcon },
  { value: "desktop", label: "Desktop", Icon: MonitorIcon },
  { value: "auto", label: "Auto", Icon: null },
];

interface ViewModeToggleProps {
  /** "floating": fixed corner button, unobtrusive. "inline": normal flow, e.g. on the profile page. */
  variant?: "floating" | "inline";
  /** Shrinks the control further, for the tiny floating button on the mobile shell. */
  compact?: boolean;
}

/** Segmented "Mobiel / Desktop / Auto" control with ARIA radiogroup semantics and arrow-key navigation. */
export function ViewModeToggle({ variant = "inline", compact = false }: ViewModeToggleProps) {
  const { preference, setPreference } = useViewMode();
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  function focusAndSelect(index: number) {
    const option = OPTIONS[index];
    setPreference(option.value);
    optionRefs.current[index]?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusAndSelect((index + 1) % OPTIONS.length);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusAndSelect((index - 1 + OPTIONS.length) % OPTIONS.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusAndSelect(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusAndSelect(OPTIONS.length - 1);
    }
  }

  const groupClassName = [styles.group, variant === "floating" ? styles.floating : "", compact ? styles.compact : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={groupClassName} role="radiogroup" aria-label="Weergave: mobiel of desktop">
      {OPTIONS.map((option, index) => {
        const isSelected = option.value === preference;
        return (
          <button
            key={option.value}
            ref={(element) => {
              optionRefs.current[index] = element;
            }}
            type="button"
            role="radio"
            aria-checked={isSelected}
            tabIndex={isSelected ? 0 : -1}
            className={isSelected ? `${styles.option} ${styles.optionSelected}` : styles.option}
            onClick={() => setPreference(option.value)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {option.Icon && <option.Icon aria-hidden="true" className={styles.icon} />}
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
