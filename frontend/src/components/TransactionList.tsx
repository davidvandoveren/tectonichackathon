import type { Transaction } from "../api/types";
import { formatDateGroup, groupByDate } from "../lib/dates";
import { formatMoney } from "../lib/money";
import { CategoryIcon } from "./icons/CategoryIcon";
import { EmptyState } from "./EmptyState";
import styles from "./TransactionList.module.css";

interface TransactionListProps {
  transactions: Transaction[];
}

export function TransactionList({ transactions }: TransactionListProps) {
  if (transactions.length === 0) {
    return <EmptyState message="Nog geen transacties op deze rekening." />;
  }

  const groups = groupByDate(transactions, (transaction) => transaction.booked_at);

  return (
    <div className={styles.list}>
      {groups.map((group) => (
        <section key={group.dateIso} aria-label={formatDateGroup(group.dateIso)}>
          <h3 className={styles.dateHeading}>{formatDateGroup(group.dateIso)}</h3>
          <ul className={styles.items}>
            {group.items.map((transaction) => {
              const isPositive = !transaction.amount.startsWith("-");
              return (
                <li key={transaction.id} className={styles.item}>
                  <span className={styles.iconWrap}>
                    <CategoryIcon category={transaction.category} aria-hidden="true" />
                  </span>
                  <div className={styles.details}>
                    <p className={styles.description}>{transaction.description}</p>
                    <p className={styles.counterparty}>{transaction.counterparty}</p>
                  </div>
                  <p className={isPositive ? styles.amountPositive : styles.amount}>
                    {formatMoney(transaction.amount, transaction.currency)}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
