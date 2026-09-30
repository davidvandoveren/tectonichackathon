import { NavLink } from "react-router";
import { WalletIcon } from "./icons/WalletIcon";
import { TransferIcon } from "./icons/TransferIcon";
import { ProfileIcon } from "./icons/ProfileIcon";
import styles from "./TabBar.module.css";

const TABS = [
  { to: "/", label: "Betalen", Icon: WalletIcon, end: true },
  { to: "/transfer", label: "Overschrijven", Icon: TransferIcon, end: false },
  { to: "/profile", label: "Profiel", Icon: ProfileIcon, end: false },
] as const;

export function TabBar() {
  return (
    <nav className={styles.bar} aria-label="Hoofdnavigatie">
      {TABS.map(({ to, label, Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? `${styles.tab} ${styles.active}` : styles.tab)}
        >
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
