import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

type ButtonVariant = "primary" | "secondary";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
}

export function Button({ variant = "primary", fullWidth = false, className, ...rest }: ButtonProps) {
  const classes = [styles.button, styles[variant], fullWidth ? styles.fullWidth : ""]
    .filter(Boolean)
    .join(" ");
  return <button className={className ? `${classes} ${className}` : classes} {...rest} />;
}
