import { useId, useState } from "react";
import { Link } from "react-router";
import { isSafeInternalPath } from "../lib/cta";
import type { Insight } from "../api/types";
import { KateConfirm } from "../skills/KateConfirm";
import type { FeedAction } from "../skills/skillsApi";
import { ChevronDownIcon } from "./icons/ChevronDownIcon";
import styles from "./InsightCard.module.css";

interface InsightCardProps {
  insight: Insight;
  /** What Kate can do for this card (Kate Skills). Without it the card only links onward. */
  action?: FeedAction;
  onDismissed?: () => void;
}

/**
 * The personalization slot: one "Voor jou" insight with an expandable
 * "Waarom zie ik dit?" explanation. `cta_target` is only followed when it is
 * a safe, root-relative internal path (see src/lib/cta.ts).
 */
export function InsightCard({ insight, action, onDismissed }: InsightCardProps) {
  const [showReason, setShowReason] = useState(false);
  const reasonId = useId();
  // A confirmable Kate action replaces the plain link: one clear next step per card.
  const canFollowCta = isSafeInternalPath(insight.cta_target) && !action?.can_confirm;

  return (
    <article className={styles.card}>
      <p className={styles.kind}>Kate</p>
      <h3 className={styles.title}>{insight.title}</h3>
      <p className={styles.body}>{insight.body}</p>

      {action && <KateConfirm action={action} onDismissed={onDismissed ?? (() => undefined)} />}

      {canFollowCta && (
        <Link to={insight.cta_target} className={styles.cta}>
          {insight.cta_label}
        </Link>
      )}

      <button
        type="button"
        className={styles.reasonToggle}
        aria-expanded={showReason}
        aria-controls={reasonId}
        onClick={() => setShowReason((value) => !value)}
      >
        <span>Waarom zie ik dit?</span>
        <ChevronDownIcon className={showReason ? styles.chevronOpen : styles.chevron} aria-hidden="true" />
      </button>
      {showReason && (
        <p id={reasonId} className={styles.reason}>
          {insight.reason}
        </p>
      )}
    </article>
  );
}
