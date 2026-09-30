import { Link } from "react-router";
import styles from "./NotFoundPage.module.css";

export function NotFoundPage() {
  return (
    <div className={styles.page}>
      <h1>Pagina niet gevonden</h1>
      <p>De pagina die je zoekt bestaat niet.</p>
      <Link to="/">Terug naar Home</Link>
    </div>
  );
}
