import { Link } from "react-router";
import type { Account, Insight } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { greeting } from "../lib/dates";
import { formatIban } from "../lib/iban";
import { splitMoney } from "../lib/money";
import type { FeedAction } from "../skills/skillsApi";
import { SparkleIcon } from "../kate/icons";
import { openKate } from "../kate/openKate";
import { InsightCarousel } from "./InsightCarousel";
import { Skeleton } from "./Skeleton";
import { ErrorState } from "./ErrorState";
import { TransferIcon } from "./icons/TransferIcon";
import { DocumentIcon } from "./icons/DocumentIcon";
import { PeopleIcon } from "./icons/PeopleIcon";
import { ChannelNotification } from "../moments/ChannelNotification";
import { SilencedList } from "../moments/SilencedList";
import type { KateFeed } from "../moments/momentsApi";
import styles from "./MobileHome.module.css";

interface Loadable<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

interface MobileHomeProps {
  accounts: Loadable<Account[]>;
  insights: Loadable<Insight[]>;
  feedActions: Record<string, FeedAction>;
  onInsightDismissed: (id: string) => void;
  kateFeed: KateFeed;
}

const TYPE_LABEL: Record<Account["type"], string> = {
  current: "Zichtrekening",
  savings: "Spaarrekening",
  credit_card: "Kredietkaart",
};

function Amount({ account }: { account: Account }) {
  const parts = splitMoney(account.balance, account.currency);
  return (
    <span className={parts.sign ? `${styles.amount} ${styles.negative}` : styles.amount}>
      {parts.sign}
      {parts.integer}
      <small>
        ,{parts.decimals} {parts.currency}
      </small>
    </span>
  );
}

/** The KBC Mobile "Start" screen: greeting, swipeable account cards, shortcuts and Kate's cards. */
export function MobileHome({ accounts, insights, feedActions, onInsightDismissed, kateFeed }: MobileHomeProps) {
  const { user } = useAuth();
  const list = accounts.data ?? [];

  return (
    <div className={styles.page}>
      <ChannelNotification items={kateFeed.items} />
      <h1 className={styles.greeting}>
        {greeting()}
        {user ? `, ${user.first_name}` : ""}
      </h1>

      {accounts.isLoading && <Skeleton height={148} />}
      {accounts.error && <ErrorState message={accounts.error} />}
      {list.length > 0 && (
        <ul className={styles.cards} aria-label="Je rekeningen">
          {list.map((account) => (
            <li key={account.id} className={styles.cardItem}>
              <Link
                to={`/accounts/${account.id}`}
                className={account.type === "current" ? `${styles.card} ${styles.primary}` : styles.card}
              >
                <span className={styles.cardType}>{TYPE_LABEL[account.type]}</span>
                <span className={styles.cardName}>{account.name}</span>
                <span className={styles.cardIban}>{formatIban(account.iban)}</span>
                <Amount account={account} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <nav className={styles.shortcuts} aria-label="Snelkoppelingen">
        <Link to="/transfer" className={styles.shortcut}>
          <span className={styles.shortcutIcon}>
            <TransferIcon aria-hidden="true" />
          </span>
          Overschrijven
        </Link>
        <Link to="/subscriptions" className={styles.shortcut}>
          <span className={styles.shortcutIcon}>
            <DocumentIcon aria-hidden="true" />
          </span>
          Abonnementen
        </Link>
        <Link to="/family" className={styles.shortcut}>
          <span className={styles.shortcutIcon}>
            <PeopleIcon aria-hidden="true" />
          </span>
          Gezin
        </Link>
        <button type="button" className={styles.shortcut} onClick={openKate}>
          <span className={`${styles.shortcutIcon} ${styles.kateIcon}`}>
            <SparkleIcon width={22} height={22} aria-hidden="true" />
          </span>
          Vraag Kate
        </button>
      </nav>

      <section className={styles.section} aria-labelledby="mobile-insights">
        <h2 id="mobile-insights" className={styles.sectionTitle}>
          Kate · Voor jou
        </h2>
        {insights.isLoading && <Skeleton height={160} />}
        {insights.error && <ErrorState message={insights.error} />}
        {insights.data && (
          <InsightCarousel insights={insights.data} actions={feedActions} onDismissed={onInsightDismissed} />
        )}
        <SilencedList silenced={kateFeed.silenced} />
      </section>
    </div>
  );
}
