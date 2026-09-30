import { Link } from "react-router";
import type { Account } from "../api/types";
import { splitMoney } from "../lib/money";
import { formatIban } from "../lib/iban";
import { WalletIcon } from "./icons/WalletIcon";
import { TransferIcon } from "./icons/TransferIcon";
import styles from "./AccountCard.module.css";

interface AccountCardProps {
  account: Account;
  /** "grid" (default tile) or "list" (compact row), toggled from the Betalen page. */
  layout?: "grid" | "list";
}

export function AccountCard({ account, layout = "grid" }: AccountCardProps) {
  const isOverdrawn = account.type === "current" && account.balance.trim().startsWith("-");
  const parts = splitMoney(account.balance, account.currency);

  return (
    <article className={layout === "list" ? `${styles.tile} ${styles.list}` : styles.tile}>
      {isOverdrawn && <span className={styles.stamp}>In overschrijding</span>}

      <span className={styles.iconWrap} aria-hidden="true">
        <WalletIcon />
      </span>

      <div className={styles.info}>
        <p className={styles.name}>{account.name}</p>
        <p className={styles.iban}>{formatIban(account.iban)}</p>
      </div>

      <Link
        to={`/transfer?from=${account.id}`}
        className={styles.swapButton}
        aria-label={`Overschrijven vanaf ${account.name}`}
        onClick={(event) => event.stopPropagation()}
      >
        <TransferIcon aria-hidden="true" />
      </Link>

      <p className={isOverdrawn ? `${styles.amount} ${styles.amountNegative}` : styles.amount}>
        {parts.sign}
        {parts.integer}
        <span className={styles.amountFraction}>
          ,{parts.decimals} {parts.currency}
        </span>
      </p>

      <Link to={`/accounts/${account.id}`} className={styles.stretchLink} aria-label={account.name} />
    </article>
  );
}
