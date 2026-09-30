import { Link } from "react-router";
import type { Account } from "../api/types";
import { formatMoney } from "../lib/money";
import { formatIban } from "../lib/iban";
import styles from "./AccountCard.module.css";

const TYPE_LABELS: Record<Account["type"], string> = {
  current: "Zichtrekening",
  savings: "Spaarrekening",
  credit_card: "Kredietkaart",
};

interface AccountCardProps {
  account: Account;
}

export function AccountCard({ account }: AccountCardProps) {
  return (
    <Link to={`/accounts/${account.id}`} className={styles.card}>
      <div className={styles.info}>
        <p className={styles.name}>{account.name}</p>
        <p className={styles.meta}>
          {TYPE_LABELS[account.type]} · {formatIban(account.iban)}
        </p>
      </div>
      <p className={styles.balance}>{formatMoney(account.balance, account.currency)}</p>
    </Link>
  );
}
