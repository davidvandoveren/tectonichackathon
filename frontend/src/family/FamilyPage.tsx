import { useEffect, useId, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { getAccounts } from "../api/accounts";
import type { Account } from "../api/types";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { SelectField } from "../components/SelectField";
import { Skeleton } from "../components/Skeleton";
import { TextField } from "../components/TextField";
import { ChevronDownIcon } from "../components/icons/ChevronDownIcon";
import { formatDateLong } from "../lib/dates";
import { formatMoney, isValidAmount, toAmountString } from "../lib/money";
import {
  ROLE_LABELS,
  SHARE_LABELS,
  acceptLink,
  contribute,
  createPot,
  endLink,
  getFamily,
  getSharedAccounts,
  invite,
  setSharing,
  type FamilyLink,
  type FamilyOverview,
  type FamilySuggestion,
  type Pot,
  type Role,
  type ShareLevel,
  type SharedAccount,
} from "./familyApi";
import styles from "./FamilyPage.module.css";

const eur = (amount: string) => formatMoney(amount, "EUR");
const LEVELS = Object.keys(SHARE_LABELS) as ShareLevel[];
const ROLES = Object.keys(ROLE_LABELS) as Role[];

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function FamilyPage() {
  const [data, setData] = useState<FamilyOverview | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load(signal?: AbortSignal) {
    getFamily(signal)
      .then((overview) => {
        setData(overview);
        setError(null);
      })
      .catch((err: unknown) => {
        if (signal?.aborted) return;
        setError(errorText(err, "Kan je familiekring niet laden."));
      });
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    getAccounts(controller.signal)
      .then(setAccounts)
      .catch(() => setAccounts([]));
    return () => controller.abort();
  }, []);

  const reload = () => load();

  return (
    <div className={styles.page}>
      <PageHeader title="Familiekring" showBack />
      <div className={styles.content}>
        {!data && !error && (
          <>
            <Skeleton height={120} />
            <Skeleton height={96} />
            <Skeleton height={96} />
          </>
        )}
        {error && <ErrorState message={error} onRetry={reload} />}
        {data && (
          <Overview data={data} accounts={accounts} onChanged={reload} />
        )}
      </div>
    </div>
  );
}

function Overview({
  data,
  accounts,
  onChanged,
}: {
  data: FamilyOverview;
  accounts: Account[];
  onChanged: () => void;
}) {
  const active = data.links.filter((l) => l.status === "active");
  const incoming = data.links.filter((l) => l.direction === "incoming");
  const outgoing = data.links.filter((l) => l.direction === "outgoing");

  return (
    <>
      <section className={styles.summary} aria-label="Samenvatting">
        <p className={styles.summaryLabel}>Jouw kring</p>
        <p className={styles.summaryAmount}>
          {active.length} {active.length === 1 ? "persoon" : "personen"}
          <span>
            {" "}
            · {data.pots.length} {data.pots.length === 1 ? "potje" : "potjes"}
          </span>
        </p>
        <p className={styles.summaryMeta}>
          Niemand ziet iets zonder jouw ja. Jij kiest per persoon wat je deelt,
          en je kan elke link stopzetten.
        </p>
        {data.me.minor && data.me.adult_on && (
          <p className={styles.notice} role="status">
            Tot je 18 wordt ({formatDateLong(data.me.adult_on)}) zien je ouders
            je saldo. Daarna beslis jij.
          </p>
        )}
      </section>

      {data.suggestions.length > 0 && (
        <section aria-labelledby="kate-heading">
          <h2 id="kate-heading" className={styles.sectionTitle}>
            Kate merkte op
          </h2>
          <div className={styles.stack}>
            {data.suggestions.map((s) => (
              <SuggestionCard key={s.id} suggestion={s} />
            ))}
          </div>
        </section>
      )}

      {incoming.length > 0 && (
        <section aria-labelledby="invites-heading">
          <h2 id="invites-heading" className={styles.sectionTitle}>
            Uitnodigingen voor jou
          </h2>
          <div className={styles.stack}>
            {incoming.map((l) => (
              <InviteCard key={l.id} link={l} onChanged={onChanged} />
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="people-heading">
        <h2 id="people-heading" className={styles.sectionTitle}>
          Mensen in je kring
        </h2>
        {active.length === 0 ? (
          <EmptyState message="Je bent nog met niemand gekoppeld." />
        ) : (
          <div className={styles.stack}>
            {active.map((l) => (
              <PersonCard key={l.id} link={l} onChanged={onChanged} />
            ))}
          </div>
        )}
        {outgoing.length > 0 && (
          <ul
            className={styles.pendingList}
            aria-label="Verstuurde uitnodigingen"
          >
            {outgoing.map((l) => (
              <li key={l.id}>
                <span>
                  Uitnodiging verstuurd naar <strong>{l.other_name}</strong>
                </span>
                <CancelButton link={l} onChanged={onChanged} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="pots-heading">
        <h2 id="pots-heading" className={styles.sectionTitle}>
          Gedeelde potjes
        </h2>
        {data.pots.length === 0 ? (
          <EmptyState message="Nog geen gedeelde potjes." />
        ) : (
          <div className={styles.stack}>
            {data.pots.map((p) => (
              <PotCard
                key={p.id}
                pot={p}
                accounts={accounts}
                onChanged={onChanged}
              />
            ))}
          </div>
        )}
      </section>

      {!data.me.minor && (
        <>
          <InviteForm onChanged={onChanged} />
          {active.length > 0 && (
            <NewPotForm links={active} onChanged={onChanged} />
          )}
        </>
      )}

      <p className={styles.privacy}>
        Een link maken we nooit op basis van je betalingen: alleen als jullie
        allebei ja zeggen. Gevoelige uitgaven (zoals gezondheid) zijn nooit
        zichtbaar voor je kring, ook niet voor een partner of ouder.
      </p>
    </>
  );
}

function Reason({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <>
      <button
        type="button"
        className={styles.reasonToggle}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
      >
        Waarom zie ik dit?
        <ChevronDownIcon
          className={open ? styles.chevronOpen : styles.chevron}
          aria-hidden="true"
        />
      </button>
      {open && (
        <p id={id} className={styles.reason}>
          {text}
        </p>
      )}
    </>
  );
}

function SuggestionCard({ suggestion }: { suggestion: FamilySuggestion }) {
  return (
    <article className={styles.highlight}>
      <p className={styles.highlightTitle}>{suggestion.title}</p>
      <p className={styles.highlightBody}>{suggestion.body}</p>
      <Reason text={suggestion.reason} />
    </article>
  );
}

function ShareSelect({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: ShareLevel;
  onChange: (level: ShareLevel) => void;
  disabled?: boolean;
}) {
  return (
    <SelectField
      label={label}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as ShareLevel)}
    >
      {LEVELS.map((level) => (
        <option key={level} value={level}>
          {SHARE_LABELS[level]}
        </option>
      ))}
    </SelectField>
  );
}

function InviteCard({
  link,
  onChanged,
}: {
  link: FamilyLink;
  onChanged: () => void;
}) {
  const [share, setShare] = useState<ShareLevel>("exists");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(errorText(err, "Dat lukte niet."));
      setBusy(false);
    }
  }

  return (
    <article className={styles.card}>
      <p className={styles.name}>{link.other_name}</p>
      <p className={styles.meta}>
        wil je toevoegen als {ROLE_LABELS[link.my_role].toLowerCase()} · deelt
        met jou: {SHARE_LABELS[link.they_share].toLowerCase()}
      </p>
      <ShareSelect
        label="Wat deel jij?"
        value={share}
        onChange={setShare}
        disabled={busy}
      />
      <div className={styles.actions}>
        <Button
          type="button"
          disabled={busy}
          onClick={() => void run(() => acceptLink(link.id, share))}
        >
          Ja, koppel ons
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={busy}
          onClick={() => void run(() => endLink(link.id))}
        >
          Nee, bedankt
        </Button>
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

function CancelButton({
  link,
  onChanged,
}: {
  link: FamilyLink;
  onChanged: () => void;
}) {
  return (
    <button
      type="button"
      className={styles.linkButton}
      onClick={() => void endLink(link.id).then(onChanged)}
    >
      Intrekken
    </button>
  );
}

function PersonCard({
  link,
  onChanged,
}: {
  link: FamilyLink;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<SharedAccount[] | null>(null);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const firstName = link.other_name.split(" ")[0];
  const g = link.guardianship;

  async function changeShare(level: ShareLevel) {
    setBusy(true);
    setError(null);
    try {
      await setSharing(link.id, level);
      onChanged();
    } catch (err) {
      setError(errorText(err, "Opslaan mislukt."));
    } finally {
      setBusy(false);
    }
  }

  async function toggleAccounts() {
    if (accounts) {
      setAccounts(null);
      return;
    }
    try {
      setAccounts(await getSharedAccounts(link.id));
    } catch (err) {
      setError(errorText(err, "Kan saldo's niet laden."));
    }
  }

  async function end() {
    setBusy(true);
    try {
      await endLink(link.id);
      onChanged();
    } catch (err) {
      setError(errorText(err, "Stopzetten mislukt."));
      setBusy(false);
    }
  }

  return (
    <article className={styles.card}>
      <div className={styles.cardTop}>
        <span className={styles.avatar} aria-hidden="true">
          {link.other_name.charAt(0).toUpperCase()}
        </span>
        <div className={styles.cardMain}>
          <p className={styles.name}>{link.other_name}</p>
          <p className={styles.meta}>
            {ROLE_LABELS[link.their_role]} · gekoppeld sinds{" "}
            {formatDateLong(link.since)}
          </p>
          {g && (
            <p className={g.active ? styles.badgeLegal : styles.badgeEnded}>
              {g.active
                ? `Wettelijke voogdij tot ${formatDateLong(g.ends_on)}`
                : `Voogdij stopte op ${formatDateLong(g.ends_on)}`}
            </p>
          )}
        </div>
      </div>

      <dl className={styles.shares}>
        <div>
          <dt>{firstName} deelt met jou</dt>
          <dd>{SHARE_LABELS[link.they_share]}</dd>
        </div>
      </dl>
      <ShareSelect
        label="Jij deelt met hen"
        value={link.i_share}
        onChange={changeShare}
        disabled={busy}
      />
      {g?.active && g.my_side === "ward" && (
        <p className={styles.hint}>
          Je keuze geldt vanaf je 18de. Tot dan ziet je ouder je saldo, zo zegt
          de wet het.
        </p>
      )}

      <div className={styles.actions}>
        {link.can_view_accounts && (
          <Button
            type="button"
            variant="secondary"
            onClick={() => void toggleAccounts()}
          >
            {accounts ? "Verberg saldo's" : `Saldo's van ${firstName}`}
          </Button>
        )}
        {link.can_end &&
          (confirmEnd ? (
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={() => void end()}
            >
              Ja, stop de link
            </Button>
          ) : (
            <button
              type="button"
              className={styles.linkButton}
              onClick={() => setConfirmEnd(true)}
            >
              Link stopzetten
            </button>
          ))}
      </div>
      {accounts && (
        <ul
          className={styles.accountList}
          aria-label={`Saldo's van ${firstName}`}
        >
          {accounts.map((a) => (
            <li key={a.name}>
              <span>{a.name}</span>
              <strong>{formatMoney(a.balance, a.currency)}</strong>
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

function PotCard({
  pot,
  accounts,
  onChanged,
}: {
  pot: Pot;
  accounts: Account[];
  onChanged: () => void;
}) {
  const payable = accounts.filter((a) => a.type === "current");
  const [open, setOpen] = useState(false);
  const [from, setFrom] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fromAccount = from || payable[0]?.id || "";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!isValidAmount(amount)) {
      setError("Geef een bedrag tussen € 0,01 en € 10.000.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await contribute(pot.id, {
        from_account_id: fromAccount,
        amount: toAmountString(amount),
        note,
      });
      setOpen(false);
      setAmount("");
      setNote("");
      onChanged();
    } catch (err) {
      setError(errorText(err, "Bijdragen mislukt."));
    } finally {
      setBusy(false);
    }
  }

  const accessLabel = {
    owner: "Jouw potje",
    pot: `Van ${pot.owner_name} · je ziet alle bijdragen`,
    gift: `Van ${pot.owner_name} · je mag bijdragen`,
  }[pot.access];

  return (
    <article className={styles.card}>
      <div className={styles.cardTop}>
        <div className={styles.cardMain}>
          <p className={styles.name}>{pot.name}</p>
          <p className={styles.meta}>{accessLabel}</p>
        </div>
        <p className={styles.amount}>
          {eur(pot.balance)}
          {pot.goal && <span>van {eur(pot.goal)}</span>}
        </p>
      </div>
      {pot.progress_percent !== null && (
        <div
          className={styles.progress}
          role="progressbar"
          aria-valuenow={pot.progress_percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${pot.name}: ${pot.progress_percent}%`}
        >
          <span style={{ width: `${pot.progress_percent}%` }} />
        </div>
      )}
      {pot.members && pot.members.length > 0 && (
        <p className={styles.meta}>Gedeeld met {pot.members.join(", ")}</p>
      )}
      {pot.contributions.length > 0 && (
        <ul className={styles.contributions} aria-label="Bijdragen">
          {pot.contributions.slice(0, 5).map((c, i) => (
            <li key={`${c.booked_on}-${i}`}>
              <span>
                {c.mine ? "Jij" : c.name} · {formatDateLong(c.booked_on)}
              </span>
              <strong>{eur(c.amount)}</strong>
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <form
          className={styles.form}
          onSubmit={(e) => void submit(e)}
          noValidate
        >
          <SelectField
            label="Van rekening"
            value={fromAccount}
            onChange={(e) => setFrom(e.target.value)}
          >
            {payable.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({eur(a.balance)})
              </option>
            ))}
          </SelectField>
          <TextField
            label="Bedrag"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="50,00"
          />
          <TextField
            label="Berichtje (optioneel)"
            value={note}
            maxLength={140}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className={styles.actions}>
            <Button type="submit" disabled={busy || !fromAccount}>
              Bevestig bijdrage
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setOpen(false)}
            >
              Annuleer
            </Button>
          </div>
        </form>
      ) : (
        <div className={styles.actions}>
          <Button
            type="button"
            onClick={() => setOpen(true)}
            disabled={payable.length === 0}
          >
            Bijdragen
          </Button>
        </div>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

function InviteForm({ onChanged }: { onChanged: () => void }) {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<Role>("partner");
  const [share, setShare] = useState<ShareLevel>("exists");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await invite({
        username: username.trim(),
        my_role: role,
        share,
      });
      setMessage(result.message);
      setUsername("");
      onChanged();
    } catch (err) {
      setError(errorText(err, "Uitnodigen mislukt."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="invite-heading" className={styles.card}>
      <h2 id="invite-heading" className={styles.sectionTitle}>
        Iemand uitnodigen
      </h2>
      <form className={styles.form} onSubmit={(e) => void submit(e)}>
        <TextField
          label="Gebruikersnaam"
          value={username}
          required
          maxLength={64}
          autoComplete="off"
          onChange={(e) => setUsername(e.target.value)}
          hint="In de demo: emma, jan, marie, lucas of noor."
        />
        <SelectField
          label="Ik ben hun…"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </SelectField>
        <ShareSelect label="Wat deel jij?" value={share} onChange={setShare} />
        <Button type="submit" disabled={busy || !username.trim()}>
          Verstuur uitnodiging
        </Button>
      </form>
      {message && (
        <p className={styles.hint} role="status">
          {message}
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function NewPotForm({
  links,
  onChanged,
}: {
  links: FamilyLink[];
  onChanged: () => void;
}) {
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [members, setMembers] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (goal && !isValidAmount(goal, 100000)) {
      setError("Geef een doelbedrag tot € 100.000, of laat het leeg.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createPot({
        name: name.trim(),
        goal: goal ? toAmountString(goal) : null,
        member_link_ids: members,
      });
      setName("");
      setGoal("");
      setMembers([]);
      onChanged();
    } catch (err) {
      setError(errorText(err, "Potje maken mislukt."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="pot-heading" className={styles.card}>
      <h2 id="pot-heading" className={styles.sectionTitle}>
        Nieuw gedeeld potje
      </h2>
      <form className={styles.form} onSubmit={(e) => void submit(e)}>
        <TextField
          label="Naam"
          value={name}
          required
          maxLength={40}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          label="Doel (optioneel)"
          inputMode="decimal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="5000"
        />
        <fieldset className={styles.fieldset}>
          <legend>Delen met</legend>
          {links.map((l) => (
            <label key={l.id} className={styles.checkbox}>
              <input
                type="checkbox"
                checked={members.includes(l.id)}
                onChange={(e) =>
                  setMembers((m) =>
                    e.target.checked
                      ? [...m, l.id]
                      : m.filter((id) => id !== l.id),
                  )
                }
              />
              {l.other_name}
            </label>
          ))}
          <p className={styles.hint}>
            Wat ze zien hangt af van wat jij met hen deelt: minstens "mag
            bijdragen" om het potje te zien.
          </p>
        </fieldset>
        <Button type="submit" disabled={busy || !name.trim()}>
          Maak potje
        </Button>
      </form>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
