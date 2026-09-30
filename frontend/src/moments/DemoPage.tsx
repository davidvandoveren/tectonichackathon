import { useState } from "react";
import { useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { runTimeMachine, type Scenario } from "./momentsApi";
import buttonStyles from "../components/Button.module.css";
import styles from "./DemoPage.module.css";

interface Jump {
  label: string;
  days: number;
  scenario: Scenario;
  hint: string;
}

const JUMPS: Jump[] = [
  {
    label: "+40 dagen · loon blijft uit",
    days: 40,
    scenario: "salary_missing",
    hint: "Kate merkt dat een vaste storting uitblijft en escaleert naar sms.",
  },
  {
    label: "+40 dagen · loon komt binnen",
    days: 40,
    scenario: "salary_paid",
    hint: "Alles loopt zoals verwacht: Kate blijft rustig.",
  },
  { label: "+7 dagen", days: 7, scenario: "none", hint: "Alleen de klok schuift op." },
];

/** Demo direction for the recording: the time machine, for the configured demo admin only. */
export function DemoPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function jump(target: Jump) {
    setBusy(true);
    setError(null);
    try {
      await runTimeMachine(target.days, target.scenario);
      navigate("/");
    } catch (caught: unknown) {
      setError(
        caught instanceof ApiError && caught.status === 404
          ? "Alleen beschikbaar voor de demo-admin (ADMIN_USERNAMES)."
          : "De tijdmachine werkte niet. Probeer opnieuw."
      );
      setBusy(false);
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Demo-regie</h1>
      <p className={styles.warning}>
        De tijdmachine verzet de klok voor de hele app. Herstart de server voor de volgende opname.
      </p>

      <ul className={styles.list}>
        {JUMPS.map((target) => (
          <li key={target.label} className={styles.item}>
            <button
              type="button"
              className={`${buttonStyles.button} ${buttonStyles.primary}`}
              disabled={busy}
              onClick={() => void jump(target)}
            >
              {target.label}
            </button>
            <p className={styles.hint}>{target.hint}</p>
          </li>
        ))}
      </ul>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
