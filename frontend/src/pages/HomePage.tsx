import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { getAccounts } from "../api/accounts";
import { getInsights } from "../api/insights";
import { ApiError } from "../api/client";
import type { Account, Insight } from "../api/types";
import { greeting } from "../lib/dates";
import { formatMoney, sumMoney } from "../lib/money";
import { AccountCard } from "../components/AccountCard";
import { InsightCarousel } from "../components/InsightCarousel";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { Wordmark } from "../components/Wordmark";
import styles from "./HomePage.module.css";

interface LoadState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

const INITIAL_STATE = { data: null, error: null, isLoading: true };

export function HomePage() {
  const { user } = useAuth();
  const [accountsState, setAccountsState] = useState<LoadState<Account[]>>(INITIAL_STATE);
  const [insightsState, setInsightsState] = useState<LoadState<Insight[]>>(INITIAL_STATE);

  useEffect(() => {
    const controller = new AbortController();
    getAccounts(controller.signal)
      .then((data) => setAccountsState({ data, error: null, isLoading: false }))
      .catch((error: unknown) => {
        setAccountsState({
          data: null,
          error: error instanceof ApiError ? error.detail : "Kan rekeningen niet laden.",
          isLoading: false,
        });
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getInsights(controller.signal)
      .then((data) => setInsightsState({ data, error: null, isLoading: false }))
      .catch((error: unknown) => {
        setInsightsState({
          data: null,
          error: error instanceof ApiError ? error.detail : "Kan inzichten niet laden.",
          isLoading: false,
        });
      });
    return () => controller.abort();
  }, []);

  const totalBalance =
    accountsState.data && accountsState.data.length > 0
      ? formatMoney(
          sumMoney(accountsState.data.map((account) => account.balance)),
          accountsState.data[0].currency
        )
      : null;

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <Wordmark />
        <p className={styles.greeting}>
          {greeting()}, {user?.first_name}
        </p>
        <p className={styles.balanceLabel}>Totaal saldo</p>
        <p className={styles.balance}>
          {accountsState.isLoading ? <Skeleton height={36} width={160} /> : (totalBalance ?? "–")}
        </p>
      </section>

      <section className={styles.section} aria-labelledby="insights-heading">
        <h2 id="insights-heading" className={styles.sectionTitle}>
          Voor jou
        </h2>
        {insightsState.isLoading && (
          <div className={styles.padded}>
            <Skeleton height={160} />
          </div>
        )}
        {insightsState.error && (
          <div className={styles.padded}>
            <ErrorState message={insightsState.error} />
          </div>
        )}
        {insightsState.data && <InsightCarousel insights={insightsState.data} />}
      </section>

      <section className={styles.section} aria-labelledby="accounts-heading">
        <h2 id="accounts-heading" className={styles.sectionTitle}>
          Rekeningen
        </h2>
        <div className={styles.padded}>
          {accountsState.isLoading && (
            <div className={styles.accountList}>
              <Skeleton height={72} />
              <Skeleton height={72} />
            </div>
          )}
          {accountsState.error && <ErrorState message={accountsState.error} />}
          {accountsState.data && accountsState.data.length === 0 && (
            <EmptyState message="Je hebt nog geen rekeningen." />
          )}
          {accountsState.data && accountsState.data.length > 0 && (
            <div className={styles.accountList}>
              {accountsState.data.map((account) => (
                <AccountCard key={account.id} account={account} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
