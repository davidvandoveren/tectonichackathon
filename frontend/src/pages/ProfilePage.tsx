import { useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/Button";
import { MenuLink } from "../components/MenuLink";
import { DocumentIcon } from "../components/icons/DocumentIcon";
import { PageHeader } from "../components/PageHeader";
import { ViewModeToggle } from "../layout/ViewModeToggle";
import styles from "./ProfilePage.module.css";

export function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  if (!user) {
    return null;
  }

  return (
    <div className={styles.page}>
      <PageHeader title="Profiel" />
      <div className={styles.content}>
        <div className={styles.card}>
          <p className={styles.name}>
            {user.first_name} {user.last_name}
          </p>
          <p className={styles.persona}>{user.persona}</p>
          <dl className={styles.details}>
            <div className={styles.row}>
              <dt>Gebruikersnaam</dt>
              <dd>{user.username}</dd>
            </div>
            <div className={styles.row}>
              <dt>Klant-ID</dt>
              <dd>{user.id}</dd>
            </div>
          </dl>
        </div>

        <ul className={styles.menu}>
          <li>
            <MenuLink to="/subscriptions" label="Mijn abonnementen" Icon={DocumentIcon} />
          </li>
        </ul>

        <Button type="button" variant="secondary" onClick={handleLogout}>
          Afmelden
        </Button>

        <section className={styles.viewModeSection} aria-labelledby="view-mode-heading">
          <h2 id="view-mode-heading" className={styles.viewModeHeading}>
            Weergave
          </h2>
          <p className={styles.viewModeHint}>
            Kies hoe de app getoond wordt: automatisch op basis van je scherm, of altijd Mobiel/Desktop
            (handig voor demo's).
          </p>
          <ViewModeToggle />
        </section>
      </div>
    </div>
  );
}
