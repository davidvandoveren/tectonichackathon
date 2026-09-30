import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { Button } from "../components/Button";
import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Skeleton } from "../components/Skeleton";
import { formatDateLong } from "../lib/dates";
import { formatMoney, isValidAmount, toAmountString } from "../lib/money";
import { refreshNotifications } from "../notifications/notificationsApi";
import {
  changePlan,
  checkMix,
  getOverview,
  sendAnswers,
  startPlan,
  type Answers,
  type Direction,
  type Etf,
  type MixCheck,
  type Overview,
  type Plan,
} from "./investApi";
import styles from "./InvestPage.module.css";

const eur = (amount: string) => formatMoney(amount, "EUR");
const STEPS = ["Je basis", "Over jou", "Richting", "Jij kiest", "Stappenplan"] as const;

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function InvestPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [weights, setWeights] = useState<Record<string, number>>({});

  function load(signal?: AbortSignal) {
    getOverview(signal)
      .then((overview) => {
        setData(overview);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!signal?.aborted) setError(errorText(err, "Kan Beleggen niet laden."));
      });
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  const hasPlan = data?.plan && (data.plan.status === "active" || data.plan.status === "paused");

  return (
    <div className={styles.page}>
      <PageHeader title="Beleggen met Kate" showBack />
      <div className={styles.content}>
        {!data && !error && (
          <>
            <Skeleton height={140} />
            <Skeleton height={200} />
          </>
        )}
        {error && <ErrorState message={error} onRetry={() => load()} />}
        {data?.plan && <PlanView data={data} plan={data.plan} onChange={setData} onNew={() => setStep(0)} />}
        {data && !hasPlan && (
          <Wizard data={data} setData={setData} step={step} setStep={setStep} weights={weights} setWeights={setWeights} />
        )}
        <p className={styles.disclaimer}>
          Concept/prototype. Kate geeft uitleg en een richting, geen persoonlijk beleggingsadvies: jij kiest. De ETF's
          zijn fictieve voorbeelden op echte indexen, de koersen zijn gesimuleerd. Beleggen houdt risico in: je kan
          (een deel van) je inleg verliezen. Een adviseur bekijkt het graag met je.
        </p>
      </div>
    </div>
  );
}

// --- the guided steps ------------------------------------------------------------------------------
interface WizardProps {
  data: Overview;
  setData: (o: Overview) => void;
  step: number;
  setStep: (n: number) => void;
  weights: Record<string, number>;
  setWeights: (w: Record<string, number>) => void;
}

function Wizard({ data, setData, step, setStep, weights, setWeights }: WizardProps) {
  const current = step > 1 && !data.direction ? 1 : step;
  return (
    <>
      <ol className={styles.progress} aria-label="Stappen">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={index === current ? styles.progressActive : index < current ? styles.progressDone : ""}
            aria-current={index === current ? "step" : undefined}
          >
            <span>{index + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      {current === 0 && <HealthStep data={data} onNext={() => setStep(1)} />}
      {current === 1 && (
        <AnswersStep
          initial={data.answers}
          onDone={(overview) => {
            setData(overview);
            setStep(2);
          }}
          onBack={() => setStep(0)}
        />
      )}
      {current === 2 && data.direction && (
        <DirectionStep data={data} d={data.direction} onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      {current === 3 && (
        <ChooseStep
          data={data}
          weights={weights}
          setWeights={setWeights}
          onNext={() => setStep(4)}
          onBack={() => setStep(2)}
        />
      )}
      {current === 4 && <PlanStep data={data} weights={weights} onDone={setData} onBack={() => setStep(3)} />}
    </>
  );
}

function KateSays({ children }: { children: ReactNode }) {
  return (
    <div className={styles.kate}>
      <span className={styles.kateAvatar} aria-hidden="true">
        K
      </span>
      <div>{children}</div>
    </div>
  );
}

function HealthStep({ data, onNext }: { data: Overview; onNext: () => void }) {
  const h = data.health;
  return (
    <section className={styles.card} aria-labelledby="health-heading">
      <h2 id="health-heading" className={styles.heading}>
        1. Is je basis gezond?
      </h2>
      <KateSays>
        Voor we het over beleggen hebben: eerst een buffer voor onverwachte kosten. Die blijft altijd op je
        spaarrekening, wat je ook kiest.
      </KateSays>
      <dl className={styles.facts}>
        <div>
          <dt>Op je spaarrekening</dt>
          <dd>{eur(h.savings)}</dd>
        </div>
        <div>
          <dt>Je uitgaven per maand</dt>
          <dd>± {eur(h.monthly_expenses)}</dd>
        </div>
        <div>
          <dt>Buffer (blijft staan)</dt>
          <dd>{eur(h.buffer)}</dd>
        </div>
        <div className={styles.highlight}>
          <dt>Kan je beleggen</dt>
          <dd>{eur(h.investable)}</dd>
        </div>
      </dl>
      <ul className={h.status === "ready" ? styles.notesOk : styles.notesWarn}>
        {h.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      <div className={styles.actions}>
        <Button type="button" onClick={onNext}>
          {h.status === "build_buffer" ? "Toch uitleg over beleggen" : "Verder"}
        </Button>
      </div>
    </section>
  );
}

const QUESTIONS: {
  key: keyof Answers;
  label: string;
  options: { value: string; label: string }[];
}[] = [
  {
    key: "goal",
    label: "Waarvoor wil je beleggen?",
    options: [
      { value: "grow", label: "Vermogen laten groeien" },
      { value: "pension", label: "Aanvulling op mijn pensioen" },
      { value: "purchase", label: "Een aankoop (bv. een huis)" },
      { value: "income", label: "Een extra inkomen" },
    ],
  },
  {
    key: "horizon",
    label: "Wanneer heb je dit geld ten vroegste nodig?",
    options: [
      { value: "lt3", label: "Binnen 3 jaar" },
      { value: "3to5", label: "Over 3 tot 5 jaar" },
      { value: "5to10", label: "Over 5 tot 10 jaar" },
      { value: "gt10", label: "Pas na 10 jaar of later" },
    ],
  },
  {
    key: "knowledge",
    label: "Hoeveel ervaring heb je met beleggen?",
    options: [
      { value: "none", label: "Nog nooit belegd" },
      { value: "basic", label: "Ik weet wat een fonds of ETF is" },
      { value: "experienced", label: "Ik beleg al zelf" },
    ],
  },
  {
    key: "drop_reaction",
    label: "Je belegging daalt op een jaar 20%. Wat doe je?",
    options: [
      { value: "sell_all", label: "Alles verkopen" },
      { value: "worried", label: "Ongerust, maar niets doen" },
      { value: "wait", label: "Rustig afwachten" },
      { value: "buy_more", label: "Bijkopen" },
    ],
  },
];

function AnswersStep({
  initial,
  onDone,
  onBack,
}: {
  initial: Answers | null;
  onDone: (o: Overview) => void;
  onBack: () => void;
}) {
  const [answers, setAnswers] = useState<Partial<Answers>>(initial ?? {});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const complete = QUESTIONS.every((q) => answers[q.key]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete) return;
    setBusy(true);
    setError(null);
    try {
      onDone(await sendAnswers(answers as Answers));
    } catch (err) {
      setError(errorText(err, "Opslaan mislukt."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.card} aria-labelledby="answers-heading">
      <h2 id="answers-heading" className={styles.heading}>
        2. Even kennismaken
      </h2>
      <KateSays>Er zijn geen foute antwoorden. Hoe eerlijker, hoe beter de richting bij je past.</KateSays>
      <form className={styles.form} onSubmit={(e) => void submit(e)}>
        {QUESTIONS.map((q) => (
          <fieldset key={q.key} className={styles.question}>
            <legend>{q.label}</legend>
            {q.options.map((o) => (
              <label key={o.value} className={styles.option}>
                <input
                  type="radio"
                  name={q.key}
                  value={o.value}
                  checked={answers[q.key] === o.value}
                  onChange={() => setAnswers((a) => ({ ...a, [q.key]: o.value }))}
                />
                {o.label}
              </label>
            ))}
          </fieldset>
        ))}
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <div className={styles.actions}>
          <Button type="button" variant="secondary" onClick={onBack}>
            Terug
          </Button>
          <Button type="submit" disabled={!complete || busy}>
            Toon mijn richting
          </Button>
        </div>
      </form>
    </section>
  );
}

function DirectionStep({
  data,
  d,
  onNext,
  onBack,
}: {
  data: Overview;
  d: Direction;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <section className={styles.card} aria-labelledby="direction-heading">
      <h2 id="direction-heading" className={styles.heading}>
        3. Kate's richting
      </h2>
      <p className={styles.headline}>{d.headline}</p>
      <div className={styles.split} aria-hidden="true">
        <span className={styles.splitShares} style={{ width: `${d.shares_percent}%` }}>
          Aandelen {d.shares_percent}%
        </span>
        <span className={styles.splitBonds} style={{ width: `${d.bonds_percent}%` }}>
          {d.bonds_percent >= 15 ? `Obligaties ${d.bonds_percent}%` : ""}
        </span>
      </div>
      <KateSays>{d.explanation}</KateSays>
      {d.warnings.length > 0 && (
        <ul className={styles.notesWarn}>
          {d.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      <details className={styles.learn}>
        <summary>ETF's in één minuut</summary>
        <ul>
          <li>
            <strong>Een ETF</strong> is een mandje met honderden of duizenden aandelen of obligaties dat een index volgt
            (bv. MSCI World). Eén aankoop, veel spreiding.
          </li>
          <li>
            <strong>Populair bij beginners:</strong> een brede wereld-ETF als basis en elke maand een vast bedrag
            bijkopen. Zo spreid je ook in de tijd.
          </li>
          <li>
            <strong>Kosten:</strong> de jaarlijkse kost (TER) gaat van je rendement af. Breed en goedkoop is meestal
            beter dan smal en duur. Bij aankoop betaal je beurstaks (meestal {data.tob_percent.replace(".", ",")}%).
          </li>
          <li>
            <strong>Kapitaliserend of uitkerend:</strong> kapitaliserend belegt dividenden opnieuw; uitkerend keert ze
            uit, en daarop betaal je roerende voorheffing.
          </li>
          <li>
            <strong>Risico:</strong> koersen schommelen. Beleg alleen geld dat je jaren kan missen, en verkoop niet in
            paniek bij een daling.
          </li>
        </ul>
      </details>
      <div className={styles.actions}>
        <Button type="button" variant="secondary" onClick={onBack}>
          Terug
        </Button>
        <Button type="button" onClick={onNext}>
          Bekijk ETF's die passen
        </Button>
      </div>
    </section>
  );
}

const FIT_LABEL: Record<string, string> = {
  fits: "Past bij je profiel",
  addition: "Aanvulling",
  caution: "Opgelet",
  not_for_you: "Niet voor jou",
};
const FIT_ORDER = ["fits", "addition", "caution", "not_for_you"];

function ChooseStep({
  data,
  weights,
  setWeights,
  onNext,
  onBack,
}: {
  data: Overview;
  weights: Record<string, number>;
  setWeights: (w: Record<string, number>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [latest, setCheck] = useState<MixCheck | null>(null);
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  const check = Object.keys(weights).length > 0 ? latest : null;
  const sorted = useMemo(
    () => [...data.catalog].sort((a, b) => FIT_ORDER.indexOf(a.fit ?? "") - FIT_ORDER.indexOf(b.fit ?? "")),
    [data.catalog]
  );

  useEffect(() => {
    if (Object.keys(weights).length === 0) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      checkMix(weights, controller.signal)
        .then(setCheck)
        .catch(() => undefined);
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [weights]);

  function toggle(etf: Etf) {
    if (etf.id in weights) {
      setWeights(Object.fromEntries(Object.entries(weights).filter(([id]) => id !== etf.id)));
    } else {
      setWeights({ ...weights, [etf.id]: Math.max(0, 100 - total) || 10 });
    }
  }

  function setWeight(id: string, value: number) {
    setWeights({ ...weights, [id]: Math.max(1, Math.min(100, Math.round(value) || 1)) });
  }

  function suggestCore() {
    const shares = data.direction?.shares_percent ?? 60;
    setWeights(shares >= 100 ? { etf_world: 100 } : { etf_world: shares, etf_aggbond: 100 - shares });
  }

  return (
    <section className={styles.card} aria-labelledby="choose-heading">
      <h2 id="choose-heading" className={styles.heading}>
        4. Jij kiest
      </h2>
      <KateSays>
        Hieronder staan voorbeeld-ETF's. Ik markeer wat bij je profiel past en waar je moet opletten, maar de keuze is
        aan jou. Veel mensen houden het simpel: een brede aandelen-ETF en een obligatie-ETF.
        <button type="button" className={styles.inlineButton} onClick={suggestCore}>
          Toon zo'n eenvoudige basismix
        </button>
      </KateSays>
      <ul className={styles.etfList}>
        {sorted.map((etf) => {
          const selected = etf.id in weights;
          return (
            <li key={etf.id} className={`${styles.etf} ${selected ? styles.etfSelected : ""}`}>
              <div className={styles.etfTop}>
                <label className={styles.etfPick}>
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={!etf.allowed && !selected}
                    onChange={() => toggle(etf)}
                  />
                  <span>
                    <strong>{etf.name}</strong>
                    <small>
                      {etf.index} · {etf.region}
                    </small>
                  </span>
                </label>
                {etf.fit && <span className={`${styles.fit} ${styles[`fit_${etf.fit}`]}`}>{FIT_LABEL[etf.fit]}</span>}
              </div>
              <p className={styles.etfText}>{etf.explanation}</p>
              <p className={styles.etfMeta}>
                Kosten {etf.ter_percent.replace(".", ",")}%/jaar · risico {etf.risk_class}/7 ·{" "}
                {etf.distributing ? "uitkerend" : "kapitaliserend"} · ± {etf.holdings.toLocaleString("nl-BE")} posities
              </p>
              {etf.fit_note && <p className={styles.fitNote}>{etf.fit_note}</p>}
              {selected && (
                <label className={styles.weight}>
                  Aandeel in je mix
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={weights[etf.id]}
                    onChange={(e) => setWeight(etf.id, Number(e.target.value))}
                  />
                  %
                </label>
              )}
            </li>
          );
        })}
      </ul>
      <div className={styles.mixSummary} role="status">
        <p>
          Samen: <strong>{total}%</strong>
          {check && check.blocked.length === 0 && (
            <>
              {" "}
              · {check.shares_percent}% aandelen · gemiddelde kost {check.yearly_cost_percent.replace(".", ",")}%/jaar
            </>
          )}
        </p>
        {check?.blocked.map((b) => (
          <p key={b} className={styles.error}>
            {b}
          </p>
        ))}
        {check && check.warnings.length > 0 && (
          <ul className={styles.notesWarn}>
            {check.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
        {check && check.blocked.length === 0 && check.warnings.length === 0 && (
          <p className={styles.ok}>✓ Deze mix past bij je richting.</p>
        )}
      </div>
      <div className={styles.actions}>
        <Button type="button" variant="secondary" onClick={onBack}>
          Terug
        </Button>
        <Button type="button" disabled={!check || check.blocked.length > 0} onClick={onNext}>
          Naar het stappenplan
        </Button>
      </div>
    </section>
  );
}

function PlanStep({
  data,
  weights,
  onDone,
  onBack,
}: {
  data: Overview;
  weights: Record<string, number>;
  onDone: (o: Overview) => void;
  onBack: () => void;
}) {
  const investable = Number(data.health.investable);
  const [amount, setAmount] = useState(String(Math.floor(Math.min(investable, 6000))));
  const [months, setMonths] = useState(12);
  const [check, setCheck] = useState<MixCheck | null>(null);
  const [accept, setAccept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    checkMix(weights, controller.signal)
      .then(setCheck)
      .catch(() => undefined);
    return () => controller.abort();
  }, [weights]);

  const valid = isValidAmount(amount, investable);
  const total = valid ? Number(toAmountString(amount)) : 0;
  const monthly = total / months;
  const drop = total * ((check?.shares_percent ?? 60) / 100) * 0.2 + total * (1 - (check?.shares_percent ?? 60) / 100) * 0.05;
  const needsAck = Boolean(check?.needs_acknowledgement) || data.direction?.suitable === false;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) {
      setError(`Kies een bedrag tot ${eur(data.health.investable)}. Je buffer blijft altijd staan.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onDone(await startPlan({ weights, total: toAmountString(amount), months, accept_risks: accept }));
      refreshNotifications();
    } catch (err) {
      setError(errorText(err, "Het plan starten lukte niet."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.card} aria-labelledby="plan-heading">
      <h2 id="plan-heading" className={styles.heading}>
        5. Stap voor stap
      </h2>
      <KateSays>
        In stappen beleggen spreidt je instapmoment: je koopt soms duur, soms goedkoop. Ik voer elke maand de stap uit
        die jij nu bevestigt, meld het je, en pauzeer vanzelf als je buffer in gevaar komt.
      </KateSays>
      <form className={styles.form} onSubmit={(e) => void submit(e)}>
        <label className={styles.field}>
          Hoeveel wil je in totaal beleggen? (max. {eur(data.health.investable)})
          <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label className={styles.field}>
          Gespreid over {months} {months === 1 ? "maand" : "maanden"}
          <input type="range" min={1} max={36} value={months} onChange={(e) => setMonths(Number(e.target.value))} />
        </label>
        {valid && (
          <dl className={styles.facts}>
            <div className={styles.highlight}>
              <dt>Per maand</dt>
              <dd>{eur(monthly.toFixed(2))}</dd>
            </div>
            <div>
              <dt>Eerste stap</dt>
              <dd>vandaag</dd>
            </div>
            <div>
              <dt>Buffer blijft staan</dt>
              <dd>{eur(data.health.buffer)}</dd>
            </div>
            <div>
              <dt>Bij een daling van 20%*</dt>
              <dd>− {eur(drop.toFixed(0))}</dd>
            </div>
          </dl>
        )}
        <p className={styles.small}>
          * Illustratie: aandelen −20%, obligaties −5%. Geen voorspelling; het kan ook meer of minder zijn.
        </p>
        {needsAck && (
          <label className={styles.ack}>
            <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)} />
            Ik las Kate's waarschuwingen en kies bewust voor deze mix.
          </label>
        )}
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <div className={styles.actions}>
          <Button type="button" variant="secondary" onClick={onBack}>
            Terug
          </Button>
          <Button type="submit" disabled={busy || !valid || (needsAck && !accept)}>
            Bevestig mijn plan
          </Button>
        </div>
      </form>
    </section>
  );
}

// --- after confirming: the portfolio and the running plan ----------------------------------------
const STATUS_LABEL = { active: "Loopt", paused: "Gepauzeerd", stopped: "Gestopt", completed: "Afgerond" };

function PlanView({
  data,
  plan,
  onChange,
  onNew,
}: {
  data: Overview;
  plan: Plan;
  onChange: (o: Overview) => void;
  onNew: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const gain = Number(data.portfolio.value) - Number(data.portfolio.invested);

  async function act(action: "pause" | "resume" | "stop") {
    setBusy(true);
    setError(null);
    try {
      onChange(await changePlan(action));
      refreshNotifications();
    } catch (err) {
      setError(errorText(err, "Dat lukte niet."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className={styles.summary} aria-label="Je beleggingen">
        <p className={styles.summaryLabel}>Je ETF's bij Bolero (gesimuleerd)</p>
        <p className={styles.summaryAmount}>{eur(data.portfolio.value)}</p>
        <p className={styles.summaryMeta}>
          Ingelegd {eur(data.portfolio.invested)} · {gain >= 0 ? "+" : "−"}
          {eur(Math.abs(gain).toFixed(2))}
        </p>
      </section>
      <section className={styles.card} aria-labelledby="plan-status">
        <h2 id="plan-status" className={styles.heading}>
          Je stappenplan · {STATUS_LABEL[plan.status]}
        </h2>
        <div
          className={styles.bar}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={plan.months}
          aria-valuenow={plan.steps.length}
          aria-label={`Stap ${plan.steps.length} van ${plan.months}`}
        >
          <span style={{ width: `${(plan.steps.length / plan.months) * 100}%` }} />
        </div>
        <p className={styles.small}>
          Stap {plan.steps.length} van {plan.months} · {eur(plan.invested)} van {eur(plan.total)} ·{" "}
          {eur(plan.monthly)} per maand
          {plan.next_on && plan.status === "active" ? ` · volgende stap ${formatDateLong(plan.next_on)}` : ""}
        </p>
        {plan.pause_reason && <p className={styles.notesWarnSingle}>{plan.pause_reason}</p>}
        <ul className={styles.holdings}>
          {data.portfolio.holdings.map((h) => (
            <li key={h.etf_id}>
              <span>
                {h.name}
                <small>
                  {plan.weights[h.etf_id] ?? 0}% · {Number(h.units).toLocaleString("nl-BE")} stuks
                </small>
              </span>
              <strong>{eur(h.value)}</strong>
            </li>
          ))}
        </ul>
        <div className={styles.actions}>
          {plan.status === "active" && (
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void act("pause")}>
              Pauzeer
            </Button>
          )}
          {plan.status === "paused" && (
            <Button type="button" disabled={busy} onClick={() => void act("resume")}>
              Hervat
            </Button>
          )}
          {(plan.status === "active" || plan.status === "paused") && (
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void act("stop")}>
              Stop het plan
            </Button>
          )}
          {(plan.status === "stopped" || plan.status === "completed") && (
            <Button type="button" onClick={onNew}>
              Nieuw plan
            </Button>
          )}
        </div>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <p className={styles.small}>
          Stoppen verkoopt niets: wat belegd is, blijft van jou. Je buffer van {eur(plan.buffer)} raakt Kate nooit aan.
        </p>
      </section>
    </>
  );
}
