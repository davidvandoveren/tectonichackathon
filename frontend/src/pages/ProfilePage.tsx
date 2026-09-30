import { Link, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
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
        <Link to="/subscriptions" className={styles.menuLink}>
          <span>
            <strong>Mijn abonnementen</strong>
            <small>Overzicht, prijsstijgingen en dubbele betalingen</small>
          </span>
          <span aria-hidden="true">›</span>
        </Link>
        <Link to="/family" className={styles.menuLink}>
          <span>
            <strong>Familiekring</strong>
            <small>Gekoppelde familie, wat je deelt en gedeelde potjes</small>
          </span>
          <span aria-hidden="true">›</span>
        </Link>
        <Button type="button" variant="secondary" onClick={handleLogout}>
          Afmelden
        </Button>
      </div>
    </div>
  );
}
