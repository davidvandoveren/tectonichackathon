import { useId, type SelectHTMLAttributes } from "react";
import styles from "./FormField.module.css";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
}

export function SelectField({ label, error, id, children, ...rest }: SelectFieldProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={selectId}>
        {label}
      </label>
      <select
        id={selectId}
        className={error ? `${styles.input} ${styles.inputError}` : styles.input}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        {...rest}
      >
        {children}
      </select>
      {error && (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
