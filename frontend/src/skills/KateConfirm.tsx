import { useState } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import { isSafeInternalPath } from "../lib/cta";
import { approveProposal, dismissMoment, proposeFromMoment, type FeedAction, type Outcome } from "./skillsApi";
import styles from "./KateConfirm.module.css";

interface KateConfirmProps {
  action: FeedAction;
  onDismissed: () => void;
}

/**
 * The action under a Kate card: what exactly Kate will do, and the customer's own tap.
 * Nothing happens before "Bevestig"; the server recomputes the moment and re-checks consent,
 * so the browser never decides amounts.
 */
export function KateConfirm({ action, onDismissed }: KateConfirmProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const created = await proposeFromMoment(action.moment);
      // `auto` within a mandate: Kate already did it, there is nothing left to approve.
      const done = created.status === "pending" ? await approveProposal(created.id) : created;
      if (done.outcome) setOutcome(done.outcome);
      else setError("Kate heeft dit klaargezet, maar kon het nog niet uitvoeren.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Dat lukte even niet. Probeer het opnieuw.");
    } finally {
      setBusy(false);
    }
  }

  async function decline() {
    setBusy(true);
    try {
      await dismissMoment(action.moment);
      onDismissed();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Dat lukte even niet.");
      setBusy(false);
    }
  }

  if (outcome) {
    const next = outcome.kind === "navigate" && outcome.navigate_to && isSafeInternalPath(outcome.navigate_to);
    return (
      <div className={styles.done} role="status">
        <p>{outcome.message}</p>
        {next && (
          <Link to={outcome.navigate_to as string} className={styles.primary}>
            Verder
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className={styles.box}>
      <p className={styles.label}>{action.can_confirm ? "Kate zet klaar" : "Kate kan helpen"}</p>
      <p className={styles.summary}>{action.summary}</p>
      {action.can_confirm ? (
        <div className={styles.buttons}>
          <button type="button" className={styles.primary} onClick={confirm} disabled={busy}>
            Bevestig
          </button>
          <button type="button" className={styles.secondary} onClick={decline} disabled={busy}>
            Nee, bedankt
          </button>
        </div>
      ) : (
        <p className={styles.hint}>
          Wil je dat Kate dit voor je klaarzet? Pas het aan in{" "}
          <Link to="/kate">Wat weet en mag Kate?</Link>
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
