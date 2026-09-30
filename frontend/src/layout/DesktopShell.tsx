import { useEffect, useRef, useState, type ComponentType, type ReactNode, type SVGProps } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { Wordmark } from "../components/Wordmark";
import { WalletIcon } from "../components/icons/WalletIcon";
import { TransferIcon } from "../components/icons/TransferIcon";
import { PiggyBankIcon } from "../components/icons/PiggyBankIcon";
import { HouseIcon } from "../components/icons/HouseIcon";
import { PeopleIcon } from "../components/icons/PeopleIcon";
import { CarIcon } from "../components/icons/CarIcon";
import { ProfileIcon } from "../components/icons/ProfileIcon";
import { BellIcon } from "../components/icons/BellIcon";
import { EnvelopeIcon } from "../components/icons/EnvelopeIcon";
import { ChatIcon } from "../components/icons/ChatIcon";
import { ChevronDownIcon } from "../components/icons/ChevronDownIcon";
import { DocumentIcon } from "../components/icons/DocumentIcon";
import { AskKateButton } from "../kate/AskKateButton";
import { openKate } from "../kate/openKate";
import { ViewModeToggle } from "./ViewModeToggle";
import styles from "./DesktopShell.module.css";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

interface SidebarItem {
  label: string;
  Icon: IconComponent;
  to?: string;
  isActive?: (pathname: string) => boolean;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  { label: "Betalen", Icon: WalletIcon, to: "/", isActive: (p) => p === "/" || p.startsWith("/accounts/") },
  { label: "Overschrijven", Icon: TransferIcon, to: "/transfer" },
  { label: "Sparen & Beleggen", Icon: PiggyBankIcon },
  { label: "Wonen", Icon: HouseIcon },
  { label: "Gezin", Icon: PeopleIcon },
  { label: "Voertuig", Icon: CarIcon },
  { label: "Profiel", Icon: ProfileIcon, to: "/profile" },
];

const SUBNAV_ITEMS = ["Rekeninguittreksels", "Doorlopende betalingsopdrachten", "Europese domiciliëringen"];

function contextTitle(pathname: string): string {
  if (pathname === "/profile") {
    return "Overzicht Profiel";
  }
  return "Overzicht Betalen";
}

export function DesktopShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Hoofdnavigatie">
        <Link to="/" className={styles.wordmarkLink} aria-label="KBC, naar Betalen">
          <Wordmark />
        </Link>
        <nav className={styles.nav}>
          {SIDEBAR_ITEMS.map((item) =>
            item.to ? (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive: routeActive }) => {
                  const active = item.isActive ? item.isActive(location.pathname) : routeActive;
                  return active ? `${styles.navItem} ${styles.navItemActive}` : styles.navItem;
                }}
              >
                <item.Icon aria-hidden="true" className={styles.navIcon} />
                <span>{item.label}</span>
              </NavLink>
            ) : (
              <span key={item.label} className={styles.navItem} aria-disabled="true" title="Binnenkort">
                <item.Icon aria-hidden="true" className={styles.navIcon} />
                <span>{item.label}</span>
              </span>
            )
          )}
        </nav>
      </aside>

      <div className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.headerTitle}>{contextTitle(location.pathname)}</h1>
          <div className={styles.headerActions}>
            <AskKateButton onClick={openKate} />

            <button type="button" className={styles.headerIconButton} aria-disabled="true" title="Binnenkort">
              <span className={styles.headerIconWrap}>
                <BellIcon aria-hidden="true" />
                <span className={styles.dot} aria-hidden="true" />
              </span>
              <span>Acties</span>
            </button>
            <button type="button" className={styles.headerIconButton} aria-disabled="true" title="Binnenkort">
              <span className={styles.headerIconWrap}>
                <EnvelopeIcon aria-hidden="true" />
                <span className={styles.dot} aria-hidden="true" />
              </span>
              <span>Berichten</span>
            </button>
            <button type="button" className={styles.headerIconButton} aria-disabled="true" title="Binnenkort">
              <span className={styles.headerIconWrap}>
                <ChatIcon aria-hidden="true" />
              </span>
              <span>Contact</span>
            </button>

            <div className={styles.userMenu} ref={menuRef}>
              <button
                type="button"
                className={styles.userMenuButton}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
              >
                <ProfileIcon aria-hidden="true" />
                <span>{user?.first_name?.toUpperCase() ?? ""}</span>
                <ChevronDownIcon
                  aria-hidden="true"
                  className={menuOpen ? styles.chevronOpen : styles.chevron}
                />
              </button>
              {menuOpen && (
                <div className={styles.userMenuDropdown} role="menu" aria-label="Gebruikersmenu">
                  <Link
                    to="/profile"
                    role="menuitem"
                    className={styles.userMenuItem}
                    onClick={() => setMenuOpen(false)}
                  >
                    Profiel
                  </Link>
                  <button type="button" role="menuitem" className={styles.userMenuItem} onClick={handleLogout}>
                    Afmelden
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <nav className={styles.subnav} aria-label="Snelkoppelingen Betalen">
          {SUBNAV_ITEMS.map((label) => (
            <span key={label} className={styles.subnavItem} aria-disabled="true" title="Binnenkort">
              <DocumentIcon aria-hidden="true" />
              <span>{label}</span>
            </span>
          ))}
          <span className={styles.subnavItem} aria-disabled="true" title="Binnenkort">
            <span aria-hidden="true">&hellip;</span>
            <span>Meer</span>
          </span>
        </nav>

        <main className={styles.content}>{children}</main>
      </div>

      <ViewModeToggle variant="floating" />
    </div>
  );
}
