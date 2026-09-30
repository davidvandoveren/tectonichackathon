import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import {
  LEVELS,
  getActivity,
  getDataConsent,
  getSkills,
  setActionConsent,
  setDataConsent,
  type ActivityEntry,
  type DataConsent,
  type Level,
  type Skill,
  type SkillAction,
} from "./skillsApi";
import styles from "./KateConsentPage.module.css";

const DOMAINS: Record<string, { label: string; hint: string }> = {
  income: { label: "Inkomsten", hint: "loon, pensioen en andere stortingen" },
  spending: { label: "Uitgaven", hint: "waar en hoeveel je betaalt" },
  balances: { label: "Saldi", hint: "wat er op je rekeningen staat" },
  products: { label: "Producten", hint: "je kaarten, pakketten en rekeningen" },
};

const LEVEL_LABELS: Record<Level, string> = {
  off: "Uit",
  suggest: "Alleen tippen",
  prepare: "Klaarzetten",
  auto: "Automatisch",
};

const LEVEL_HINTS: Record<Level, string> = {
  off: "Kate gebruikt dit nooit.",
  suggest: "Kate mag het vermelden, zonder iets klaar te zetten.",
  prepare: "Kate vult alles in; jij bevestigt.",
  auto: "Kate doet het zelf binnen jouw grenzen en laat het je weten.",
};

const EVENT_LABELS: Record<string, string> = {
  proposed: "Voorgesteld",
  suggested: "Getipt",
  executed: "Uitgevoerd",
  failed: "Mislukt",
  declined: "Geweigerd",
  expired: "Verlopen",
  consent_changed: "Toestemming aangepast",
};

const DEFAULT_MANDATE = { max_per_execution: "50.00", max_per_month: "200.00" };

function toMoney(value: string): string {
  const number = Number(value.replace(",", "."));
  return Number.isFinite(number) ? number.toFixed(2) : value;
}

function errorText(err: unknown): string {
  return err instanceof ApiError ? err.detail : "Dat lukte even niet. Probeer het opnieuw.";
}

/** "Wat weet en mag Kate?": what Kate may look at, what she may do, and what she did. */
export function KateConsentPage() {
  const [data, setData] = useState<DataConsent | null>(null);
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getDataConsent(controller.signal), getSkills(controller.signal), getActivity(controller.signal)])
      .then(([consent, catalogue, log]) => {
        setData(consent);
        setSkills(catalogue);
        setActivity(log);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(errorText(err));
      });
    return () => controller.abort();
  }, []);

  async function toggleDomain(domain: string, allowed: boolean) {
    try {
      setData(await setDataConsent(domain, allowed));
    } catch (err) {
      setError(errorText(err));
    }
  }

  function replaceAction(updated: SkillAction) {
    setSkills((current) =>
      current?.map((skill) => ({
        ...skill,
        actions: skill.actions.map((a) => (a.id === updated.id ? updated : a)),
      })) ?? null
    );
    getActivity().then(setActivity, () => undefined);
  }

  return (
    <div className={styles.page}>
      <PageHeader title="Wat weet en mag Kate?" showBack />
      <div className={styles.content}>
        {error && <ErrorState message={error} />}

        <section aria-labelledby="data-heading" className={styles.card}>
          <h2 id="data-heading" className={styles.sectionTitle}>
            Wat Kate mag bekijken
          </h2>
          <p className={styles.intro}>
            Staat iets uit, dan berekent Kate het niet eens. Gevoelige uitgaven (gezondheid, geloof, politiek,
            vakbond) gebruikt ze nooit.
          </p>
          {!data && !error && <Skeleton height={120} />}
          {data && (
            <ul className={styles.list}>
              {Object.entries(DOMAINS).map(([domain, { label, hint }]) => (
                <li key={domain}>
                  <label className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={data[domain] ?? false}
                      onChange={(event) => toggleDomain(domain, event.target.checked)}
                    />
                    <span>
                      <strong>{label}</strong> <span className={styles.muted}>– {hint}</span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="actions-heading" className={styles.card}>
          <h2 id="actions-heading" className={styles.sectionTitle}>
            Wat Kate voor je mag doen
          </h2>
          <p className={styles.intro}>
            Iemand anders betalen, lenen, beleggen en verzekeren gaan nooit automatisch: daar beslis jij, of een
            adviseur.
          </p>
          {!skills && !error && <Skeleton height={200} />}
          {skills?.map((skill) => (
            <div key={skill.id} className={styles.skill}>
              <h3 className={styles.skillTitle}>{skill.title}</h3>
              {skill.actions.map((action) => (
                <ActionControl key={action.id} action={action} onSaved={replaceAction} onError={setError} />
              ))}
            </div>
          ))}
        </section>

        <section aria-labelledby="activity-heading" className={styles.card}>
          <h2 id="activity-heading" className={styles.sectionTitle}>
            Wat Kate voor je deed
          </h2>
          {activity.length === 0 ? (
            <p className={styles.muted}>Nog niets. Alles wat Kate voorstelt of doet, zie je hier.</p>
          ) : (
            <ol className={styles.activity}>
              {activity.slice(0, 20).map((entry, index) => (
                <li key={`${entry.at}-${index}`}>
                  <span className={styles.event}>{EVENT_LABELS[entry.event] ?? entry.event}</span>
                  <span>{entry.summary}</span>
                  <time className={styles.muted} dateTime={entry.at}>
                    {new Date(entry.at).toLocaleString("nl-BE", { dateStyle: "short", timeStyle: "short" })}
                  </time>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

interface ActionControlProps {
  action: SkillAction;
  onSaved: (updated: SkillAction) => void;
  onError: (message: string) => void;
}

function ActionControl({ action, onSaved, onError }: ActionControlProps) {
  const allowed = LEVELS.slice(0, LEVELS.indexOf(action.max_level) + 1);
  const needsMandate = action.risk === "internal_money";
  const [pendingAuto, setPendingAuto] = useState(false);
  const [mandate, setMandate] = useState(action.mandate ?? DEFAULT_MANDATE);
  const shown: Level = pendingAuto ? "auto" : action.level;

  async function save(level: Level, withMandate: boolean) {
    try {
      const updated = await setActionConsent(
        action.id,
        level,
        withMandate
          ? { max_per_execution: toMoney(mandate.max_per_execution), max_per_month: toMoney(mandate.max_per_month) }
          : null
      );
      setPendingAuto(false);
      onSaved(updated);
    } catch (err) {
      onError(errorText(err));
    }
  }

  function choose(level: Level) {
    if (level === "auto" && needsMandate) {
      setPendingAuto(true); // nothing is saved until the customer sets their limits
      return;
    }
    setPendingAuto(false);
    void save(level, false);
  }

  return (
    <fieldset className={styles.action}>
      <legend className={styles.actionTitle}>{action.title}</legend>
      <div className={styles.levels}>
        {allowed.map((level) => (
          <label key={level} className={shown === level ? styles.levelActive : styles.level}>
            <input
              type="radio"
              name={action.id}
              value={level}
              checked={shown === level}
              onChange={() => choose(level)}
            />
            {LEVEL_LABELS[level]}
          </label>
        ))}
      </div>
      <p className={styles.muted}>{LEVEL_HINTS[shown]}</p>
      {shown === "auto" && needsMandate && (
        <div className={styles.mandate}>
          <label>
            Max. per keer (€)
            <input
              inputMode="decimal"
              value={mandate.max_per_execution}
              onChange={(event) => setMandate({ ...mandate, max_per_execution: event.target.value })}
            />
          </label>
          <label>
            Max. per maand (€)
            <input
              inputMode="decimal"
              value={mandate.max_per_month}
              onChange={(event) => setMandate({ ...mandate, max_per_month: event.target.value })}
            />
          </label>
          <button type="button" className={styles.save} onClick={() => void save("auto", true)}>
            Mandaat opslaan
          </button>
        </div>
      )}
    </fieldset>
  );
}
