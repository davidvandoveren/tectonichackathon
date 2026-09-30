import { useNavigate } from "react-router";
import { BackIcon } from "./icons/BackIcon";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  title: string;
  showBack?: boolean;
}

export function PageHeader({ title, showBack = false }: PageHeaderProps) {
  const navigate = useNavigate();
  return (
    <header className={styles.header}>
      {showBack && (
        <button type="button" className={styles.backButton} onClick={() => navigate(-1)} aria-label="Terug">
          <BackIcon aria-hidden="true" />
        </button>
      )}
      <h1 className={styles.title}>{title}</h1>
    </header>
  );
}
