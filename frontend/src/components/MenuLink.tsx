import type { ComponentType, SVGProps } from "react";
import { Link } from "react-router";
import { ChevronDownIcon } from "./icons/ChevronDownIcon";
import styles from "./MenuLink.module.css";

interface MenuLinkProps {
  to: string;
  label: string;
  Icon?: ComponentType<SVGProps<SVGSVGElement>>;
}

/**
 * A single row in a settings-style menu list: icon, label, trailing chevron.
 * Used for simple navigation links on pages like Profiel (e.g. "Mijn
 * abonnementen"). Wrap one or more in a <ul> with role="list" styling as
 * needed; each item should be its own <li>.
 */
export function MenuLink({ to, label, Icon }: MenuLinkProps) {
  return (
    <Link to={to} className={styles.link}>
      {Icon && <Icon aria-hidden="true" className={styles.icon} />}
      <span className={styles.label}>{label}</span>
      <ChevronDownIcon aria-hidden="true" className={styles.chevron} />
    </Link>
  );
}
