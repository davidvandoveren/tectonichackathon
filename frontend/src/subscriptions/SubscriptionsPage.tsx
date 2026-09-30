import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { ChevronDownIcon } from "../components/icons/ChevronDownIcon";
import { formatDateLong } from "../lib/dates";
import { formatMoney, isValidAmount, toAmountString } from "../lib/money";
import {
  GROUP_LABELS,
  addSubscription,
  getSubscriptions,
  sendSubscriptionFeedback,
  setDismissed,
  type Subscription,
  type SubscriptionsOverview,
} from "./subscriptionsApi";
import styles from "./SubscriptionsPage.module.css";

const eur = (amount: string) => formatMoney(amount, "EUR");
const UNDO_MS = 8000;

function difference(a: string, b: string): string {
  return (Number(a) - Number(b)).toFixed(2);
}

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

interface Highlight {
  key: string;
  tone: "warning" | "info";
  title: string;
  body: string;
}

/** The few things worth saying out loud; everything else stays quietly in the list. */
function highlights(subs: Subscription[]): Highlight[] {
  const result: Highlight[] = [];
  const groups = new Map<string, Subscription[]>();
  for (const sub of subs) {
    if (sub.flags.includes("duplicate") && sub.group) {
      groups.set(sub.group, [...(groups.get(sub.group) ?? []), sub]);
    }
  }
  for (const [group, members] of groups) {
    const total = members.reduce((sum, s) => sum + Number(s.amount), 0).toFixed(2);
    result.push({
      key: `dup-${group}`,
      tone: "warning",
      title: `Je betaalt voor ${members.length} ${(GROUP_LABELS[group] ?? group).toLowerCase()}diensten`,
      body: `${members.map((s) => s.name).join(" en ")} samen kosten ${eur(total)} per maand. Gebruik je ze allemaal nog?`,
    });
  }
  for (const sub of subs) {
    if (sub.flags.includes("price_increase") && sub.previous_amount) {
      result.push({
        key: `price-${sub.id}`,
        tone: "warning",
        title: `${sub.name} werd ${eur(difference(sub.amount, sub.previous_amount))} duurder`,
        body: `Van ${eur(sub.previous_amount)} naar ${eur(sub.amount)} per maand, of ${eur(sub.yearly_cost)} per jaar.`,
      });
    }
    if (sub.flags.includes("trial_converted")) {
      result.push({
        key: `trial-${sub.id}`,
        tone: "info",
        title: `Je proefperiode bij ${sub.name} is voorbij`,
        body: `Sinds ${formatDateLong(sub.first_seen)} betaal je ${eur(sub.amount)} per maand.`,
      });
    } else if (sub.is_new) {
      result.push({
        key: `new-${sub.id}`,
        tone: "info",
        title: `Nieuw abonnement gevonden: ${sub.name}`,
        body: `We zagen de eerste betalingen van ${eur(sub.amount)} per maand. Klopt dit niet? Verwijder het met één klik.`,
      });
    }
  }
  return result;
}

interface Undo {
  id: string;
  name: string;
}

export function SubscriptionsPage() {
  const [data, setData] = useState<SubscriptionsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [undo, setUndo] = useState<Undo | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const undoTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    const controller = new AbortController();
    getSubscriptions(controller.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(errorText(err, "Kan abonnementen niet laden."));
      });
    return () => {
      controller.abort();
      window.clearTimeout(undoTimer.current);
    };
  }, []);

  function onUpdated(updated: Subscription) {
    setData((current) => {
      if (!current) return current;
      const subscriptions = current.subscriptions.map((s) => (s.id === updated.id ? updated : s));
      const savings = subscriptions
        .filter((s) => s.status === "cancel_reminder")
        .reduce((sum, s) => sum + Number(s.yearly_cost), 0);
      return { ...current, subscriptions, yearly_savings: savings.toFixed(2) };
    });
  }

  async function remove(sub: Subscription) {
    setActionError(null);
    try {
      setData(await setDismissed(sub.id, true));
      setUndo({ id: sub.id, name: sub.name });
      window.clearTimeout(undoTimer.current);
      undoTimer.current = window.setTimeout(() => setUndo(null), UNDO_MS);
    } catch (err) {
      setActionError(errorText(err, "Verwijderen mislukt."));
    }
  }

  async function restore() {
    if (!undo) return;
    window.clearTimeout(undoTimer.current);
    try {
      setData(await setDismissed(undo.id, false));
    } catch (err) {
      setActionError(errorText(err, "Herstellen mislukt."));
    } finally {
      setUndo(null);
    }
  }

  return (
    <div className={styles.page}>
      <PageHeader title="Abonnementen" showBack />
      <div className={styles.content}>
        {!data && !error && (
          <>
            <Skeleton height={140} />
            <Skeleton height={96} />
            <Skeleton height={96} />
          </>
        )}
        {error && <ErrorState message={error} />}
        {actionError && (
          <p className={styles.error} role="alert">
            {actionError}
          </p>
        )}
        {data && <Overview data={data} onUpdated={onUpdated} onRemove={remove} onReplaced={setData} />}
      </div>

      {undo && (
        <div className={styles.toast} role="status">
          <span>{undo.name} verwijderd uit je lijst.</span>
          <button type="button" className={styles.toastButton} onClick={() => void restore()}>
            Ongedaan maken
          </button>
        </div>
      )}
    </div>
  );
}

interface OverviewProps {
  data: SubscriptionsOverview;
  onUpdated: (s: Subscription) => void;
  onRemove: (s: Subscription) => Promise<void>;
  onReplaced: (o: SubscriptionsOverview) => void;
}

function Overview({ data, onUpdated, onRemove, onReplaced }: OverviewProps) {
  const subs = data.subscriptions;
  const notes = highlights(subs);
  const savings = Number(data.yearly_savings) > 0;

  return (
    <>
      <section className={styles.summary} aria-label="Samenvatting">
        <p className={styles.summaryLabel}>Je abonnementen kosten</p>
        <p className={styles.summaryAmount}>
          {eur(data.monthly_total)} <span>per maand</span>
        </p>
        <p className={styles.summaryMeta}>
          {subs.length} {subs.length === 1 ? "abonnement" : "abonnementen"} · {eur(data.yearly_total)} per jaar ·
          automatisch herkend
        </p>
        {savings && (
          <p className={styles.savings} role="status">
            Als je opzegt wat je niet meer gebruikt, bespaar je {eur(data.yearly_savings)} per jaar.
          </p>
        )}
      </section>

      {notes.length > 0 && (
        <section aria-labelledby="noticed-heading">
          <h2 id="noticed-heading" className={styles.sectionTitle}>
            Kate merkte op
          </h2>
          <div className={styles.stack}>
            {notes.map((note) => (
              <article key={note.key} className={`${styles.highlight} ${styles[note.tone]}`}>
                <p className={styles.highlightTitle}>{note.title}</p>
                <p className={styles.highlightBody}>{note.body}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="all-heading">
        <h2 id="all-heading" className={styles.sectionTitle}>
          Alle abonnementen
        </h2>
        {subs.length === 0 ? (
          <EmptyState message="We zien geen terugkerende abonnementen op je rekeningen." />
        ) : (
          <div className={styles.stack}>
            {subs.map((sub) => (
              <SubscriptionCard key={sub.id} sub={sub} onUpdated={onUpdated} onRemove={onRemove} />
            ))}
          </div>
        )}
        <AddSubscription onAdded={onReplaced} />
      </section>

      <p className={styles.privacy}>
        Kate herkent je abonnementen automatisch uit je betalingen; je hoeft niets in te geven. We zien alleen{" "}
        <strong>dat</strong> je betaalt, niet <strong>of</strong> je iets gebruikt. Daarom vragen we het jou.
        {data.hidden_sensitive > 0 &&
          ` ${data.hidden_sensitive} ${data.hidden_sensitive === 1 ? "betaling analyseren" : "betalingen analyseren"} we bewust niet, omdat ze over gevoelige onderwerpen kunnen gaan (bv. gezondheid of lidmaatschappen).`}
        {data.dismissed > 0 &&
          ` ${data.dismissed} ${data.dismissed === 1 ? "betaling heb" : "betalingen heb"} je zelf uit de lijst verwijderd.`}
      </p>
    </>
  );
}

const FLAG_LABELS = {
  duplicate: "Dubbel",
  price_increase: "Duurder",
  trial_converted: "Was proef",
} as const;

interface CardProps {
  sub: Subscription;
  onUpdated: (s: Subscription) => void;
  onRemove: (s: Subscription) => Promise<void>;
}

function SubscriptionCard({ sub, onUpdated, onRemove }: CardProps) {
  const [showReason, setShowReason] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const reasonId = useId();

  async function answer(stillUsed: boolean) {
    setSaving(true);
    setError(null);
    try {
      onUpdated(await sendSubscriptionFeedback(sub.id, { still_used: stillUsed, remind_to_cancel: !stillUsed }));
      setEditing(false);
    } catch (err) {
      setError(errorText(err, "Opslaan mislukt."));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    setSaving(true);
    await onRemove(sub);
    setSaving(false);
  }

  const answered = sub.status !== "unknown" && !editing;
  const manual = sub.source === "manual";

  return (
    <article className={`${styles.card} ${sub.status === "cancel_reminder" ? styles.cardMuted : ""}`}>
      {sub.is_new && !manual && (
        <div className={styles.newBanner}>
          <span>
            <strong>Nieuw gedetecteerd.</strong> Klopt dit niet?
          </span>
          <button type="button" className={styles.removeButton} disabled={saving} onClick={() => void remove()}>
            Verwijder
          </button>
        </div>
      )}

      <div className={styles.cardTop}>
        <span className={`${styles.logo} ${styles[`group_${sub.group ?? "other"}`] ?? ""}`} aria-hidden="true">
          {sub.name.charAt(0).toUpperCase()}
        </span>
        <div className={styles.cardMain}>
          <p className={styles.name}>{sub.name}</p>
          <p className={styles.meta}>
            {sub.group ? `${GROUP_LABELS[sub.group] ?? sub.group} · ` : ""}volgende betaling {formatDateLong(sub.next_expected)}
          </p>
          {(sub.flags.length > 0 || sub.is_new || manual) && (
            <ul className={styles.flags} aria-label="Labels">
              {sub.is_new && !manual && <li className={`${styles.flag} ${styles.flag_new}`}>Nieuw</li>}
              {manual && <li className={`${styles.flag} ${styles.flag_manual}`}>Zelf toegevoegd</li>}
              {sub.flags.map((flag) => (
                <li key={flag} className={`${styles.flag} ${styles[`flag_${flag}`]}`}>
                  {FLAG_LABELS[flag]}
                </li>
              ))}
            </ul>
          )}
        </div>
        <p className={styles.amount}>
          {eur(sub.amount)}
          <span>/maand</span>
        </p>
      </div>

      {answered ? (
        <div className={styles.answer}>
          <p>
            {sub.status === "in_use"
              ? "✓ Je gebruikt dit nog. We laten het met rust."
              : `🔔 We herinneren je op ${sub.remind_on ? formatDateLong(sub.remind_on) : "tijd"} om op te zeggen, vóór de volgende betaling.`}
          </p>
          <button type="button" className={styles.linkButton} onClick={() => setEditing(true)}>
            Wijzig
          </button>
        </div>
      ) : (
        <div className={styles.question}>
          <p className={styles.questionText}>Gebruik je dit nog?</p>
          <div className={styles.answers}>
            <button type="button" className={styles.yes} disabled={saving} onClick={() => void answer(true)}>
              Ja
            </button>
            <button type="button" className={styles.no} disabled={saving} onClick={() => void answer(false)}>
              Nee, herinner me om op te zeggen
            </button>
          </div>
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </div>
      )}

      <div className={styles.cardFooter}>
        <button
          type="button"
          className={styles.reasonToggle}
          aria-expanded={showReason}
          aria-controls={reasonId}
          onClick={() => setShowReason((value) => !value)}
        >
          Waarom zie ik dit?
          <ChevronDownIcon className={showReason ? styles.chevronOpen : styles.chevron} aria-hidden="true" />
        </button>
        {!(sub.is_new && !manual) && (
          <button
            type="button"
            className={styles.quietRemove}
            disabled={saving}
            onClick={() => void remove()}
            aria-label={`${sub.name} verwijderen uit de lijst`}
          >
            {manual ? "Verwijder" : "Geen abonnement? Verwijder"}
          </button>
        )}
      </div>
      {showReason && (
        <p id={reasonId} className={styles.reason}>
          {sub.reason}
        </p>
      )}
    </article>
  );
}

function AddSubscription({ onAdded }: { onAdded: (o: SubscriptionsOverview) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [nextCharge, setNextCharge] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameId = useId();
  const amountId = useId();
  const dateId = useId();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return setError("Geef een naam.");
    if (!isValidAmount(amount, 1000)) return setError("Geef een geldig bedrag (max. € 1.000).");
    setSaving(true);
    setError(null);
    try {
      onAdded(
        await addSubscription({
          name: name.trim(),
          amount: toAmountString(amount),
          ...(nextCharge ? { next_charge: nextCharge } : {}),
        })
      );
      setName("");
      setAmount("");
      setNextCharge("");
      setOpen(false);
    } catch (err) {
      setError(errorText(err, "Toevoegen mislukt."));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className={styles.addButton} onClick={() => setOpen(true)}>
        + Abonnement zelf toevoegen
      </button>
    );
  }

  return (
    <form className={styles.addForm} onSubmit={(event) => void submit(event)}>
      <p className={styles.addTitle}>Abonnement toevoegen</p>
      <p className={styles.addHint}>Alleen nodig als we het niet zelf zien, bv. als je met een andere kaart betaalt.</p>
      <label htmlFor={nameId}>Naam</label>
      <input id={nameId} value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="bv. Streamz" />
      <label htmlFor={amountId}>Bedrag per maand (€)</label>
      <input
        id={amountId}
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        inputMode="decimal"
        placeholder="9,99"
      />
      <label htmlFor={dateId}>Volgende betaling (optioneel)</label>
      <input id={dateId} type="date" value={nextCharge} onChange={(e) => setNextCharge(e.target.value)} />
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <div className={styles.addActions}>
        <button type="button" className={styles.yes} onClick={() => setOpen(false)}>
          Annuleer
        </button>
        <button type="submit" className={styles.no} disabled={saving}>
          Toevoegen
        </button>
      </div>
    </form>
  );
}
