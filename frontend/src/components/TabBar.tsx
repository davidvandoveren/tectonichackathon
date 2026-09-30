import { NavLink } from "react-router";
import { HouseIcon } from "./icons/HouseIcon";
import { PiggyBankIcon } from "./icons/PiggyBankIcon";
import { TransferIcon } from "./icons/TransferIcon";
import { WalletIcon } from "./icons/WalletIcon";
import { SparkleIcon } from "../kate/icons";
import { openKate } from "../kate/openKate";
import styles from "./TabBar.module.css";

const LINKS = [
  { to: "/", label: "Start", Icon: HouseIcon, end: true },
  { to: "/transfer", label: "Betalen", Icon: TransferIcon, end: false },
  { to: "/invest", label: "Beleggen", Icon: PiggyBankIcon, end: false },
  { to: "/profile", label: "Mijn KBC", Icon: WalletIcon, end: false },
] as const;

/** KBC Mobile bottom navigation: Start, Betalen, Beleggen, Mijn KBC and Kate. */
export function TabBar() {
  return (
    <nav className={styles.bar} aria-label="Hoofdnavigatie">
      {LINKS.map(({ to, label, Icon, end }) => (
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
      <button type="button" className={styles.tab} onClick={openKate}>
        <SparkleIcon width={22} height={22} aria-hidden="true" />
        <span>Kate</span>
      </button>
    </nav>
  );
}
