import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { getAuthConfig, getDemoUsers } from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import type { DemoUser } from "../api/types";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import { Wordmark } from "../components/Wordmark";
import { ViewModeToggle } from "../layout/ViewModeToggle";
import styles from "./LoginPage.module.css";

interface LocationState {
  from?: { pathname: string };
}

export function LoginPage() {
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [demoUsers, setDemoUsers] = useState<DemoUser[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [passwordless, setPasswordless] = useState(false);
  const [selectedUsername, setSelectedUsername] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getDemoUsers(controller.signal), getAuthConfig(controller.signal)])
      .then(([users, config]) => {
        setDemoUsers(users);
        setPasswordless(config.passwordless_login);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof ApiError ? error.detail : "Kan de demo-profielen niet laden.");
      });
    return () => controller.abort();
  }, []);

  async function signIn(username: string) {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await (passwordless ? demoLogin(username) : login(username, password));
      const state = location.state as LocationState | null;
      const redirectTo = state?.from?.pathname ?? "/";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(
          error.status === 429 ? "Te veel pogingen. Probeer het straks opnieuw." : error.detail
        );
      } else {
        setSubmitError("Aanmelden is mislukt. Probeer het opnieuw.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedUsername) {
      setSubmitError("Kies eerst een profiel.");
      return;
    }
    void signIn(selectedUsername);
  }

  function handlePersonaClick(username: string) {
    setSelectedUsername(username);
    if (passwordless) {
      void signIn(username);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <Wordmark tone="light" />
      </div>
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <h1 className={styles.heading}>Aanmelden</h1>

        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>Kies je profiel</legend>

          {demoUsers === null && !loadError && (
            <div className={styles.userList}>
              <Skeleton height={64} />
              <Skeleton height={64} />
              <Skeleton height={64} />
            </div>
          )}

          {loadError && <ErrorState message={loadError} />}

          {demoUsers && (
            <div className={styles.userList} role="radiogroup" aria-label="Demo-profiel">
              {demoUsers.map((demoUser) => {
                const isSelected = demoUser.username === selectedUsername;
                return (
                  <button
                    key={demoUser.username}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    aria-label={passwordless ? `Aanmelden als ${demoUser.display_name}` : undefined}
                    disabled={isSubmitting}
                    className={isSelected ? `${styles.userCard} ${styles.userCardSelected}` : styles.userCard}
                    onClick={() => handlePersonaClick(demoUser.username)}
                  >
                    <span className={styles.userName}>{demoUser.display_name}</span>
                    <span className={styles.userPersona}>{demoUser.persona}</span>
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>

        {!passwordless && (
          <TextField
            label="Wachtwoord"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}

        {submitError && (
          <p className={styles.submitError} role="alert" aria-live="assertive">
            {submitError}
          </p>
        )}

        {passwordless ? (
          <p className={styles.legend} aria-live="polite">
            {isSubmitting ? "Bezig met aanmelden…" : "Tik op een profiel om meteen aan te melden."}
          </p>
        ) : (
          <Button type="submit" fullWidth disabled={isSubmitting || !selectedUsername}>
            {isSubmitting ? "Bezig met aanmelden…" : "Aanmelden"}
          </Button>
        )}
      </form>
      <p className={styles.footer}>
        Demo – synthetische data, geen echte bank en geen officiële KBC-app ·{" "}
        <Link to="/privacy">Privacy &amp; AI</Link>
      </p>
      <ViewModeToggle variant="floating" />
    </div>
  );
}
