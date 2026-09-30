import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { getAccount, getTransactions } from "../api/accounts";
import { ApiError } from "../api/client";
import type { Account, Transaction } from "../api/types";
import { formatMoney } from "../lib/money";
import { formatIban } from "../lib/iban";
import { PageHeader } from "../components/PageHeader";
import { TransactionList } from "../components/TransactionList";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import styles from "./AccountDetailPage.module.css";

const TYPE_LABELS: Record<Account["type"], string> = {
  current: "Zichtrekening",
  savings: "Spaarrekening",
  credit_card: "Kredietkaart",
};

export function AccountDetailPage() {
  const { accountId } = useParams<{ accountId: string }>();

  if (!accountId) {
    return null;
  }

  // Remounting on accountId change (via `key`) gives each account a fresh
  // loading/error state instead of resetting it imperatively inside an effect.
  return <AccountDetailContent key={accountId} accountId={accountId} />;
}

function AccountDetailContent({ accountId }: { accountId: string }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([getAccount(accountId, controller.signal), getTransactions(accountId, 50, controller.signal)])
      .then(([accountData, transactionData]) => {
        setAccount(accountData);
        setTransactions(transactionData);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          setError(err.status === 404 ? "Deze rekening bestaat niet (meer)." : err.detail);
        } else {
          setError("Kan rekeninggegevens niet laden.");
        }
      })
      .finally(() => setIsLoading(false));

    return () => controller.abort();
  }, [accountId]);

  return (
    <div className={styles.page}>
      <PageHeader title={account?.name ?? "Rekening"} showBack />

      <div className={styles.content}>
        {isLoading && (
          <div className={styles.skeletons}>
            <Skeleton height={48} />
            <Skeleton height={80} />
            <Skeleton height={80} />
          </div>
        )}

        {error && <ErrorState message={error} />}

        {account && !isLoading && !error && (
          <>
            <div className={styles.summary}>
              <p className={styles.iban}>{formatIban(account.iban)}</p>
              <p className={styles.type}>{TYPE_LABELS[account.type]}</p>
              <p className={styles.balance}>{formatMoney(account.balance, account.currency)}</p>
            </div>
            <TransactionList transactions={transactions ?? []} />
          </>
        )}
      </div>
    </div>
  );
}
