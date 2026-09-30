import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getAccounts } from "../api/accounts";
import { getInsights } from "../api/insights";
import { ApiError } from "../api/client";
import type { Account, Insight } from "../api/types";
import { AccountSection } from "../components/AccountSection";
import { InsightCarousel } from "../components/InsightCarousel";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { TileViewToggle, type TileLayout } from "../components/TileViewToggle";
import { TransferIcon } from "../components/icons/TransferIcon";
import buttonStyles from "../components/Button.module.css";
import styles from "./HomePage.module.css";

interface LoadState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

const INITIAL_STATE = { data: null, error: null, isLoading: true };

export function HomePage() {
  const [accountsState, setAccountsState] = useState<LoadState<Account[]>>(INITIAL_STATE);
  const [insightsState, setInsightsState] = useState<LoadState<Insight[]>>(INITIAL_STATE);
  const [tileLayout, setTileLayout] = useState<TileLayout>("grid");

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

  const accounts = accountsState.data ?? [];
  const currentAccounts = accounts.filter((account) => account.type === "current");
  const savingsAccounts = accounts.filter((account) => account.type === "savings");
  const creditCardAccounts = accounts.filter((account) => account.type === "credit_card");

  return (
    <div className={styles.page}>
      <div className={styles.titleRow}>
        <h1 className={styles.title}>Betalen</h1>
        <div className={styles.titleActions}>
          <TileViewToggle value={tileLayout} onChange={setTileLayout} />
          <Link to="/transfer" className={`${buttonStyles.button} ${buttonStyles.primary}`}>
            <TransferIcon aria-hidden="true" />
            Overschrijving
          </Link>
        </div>
      </div>

      <section className={styles.section} aria-labelledby="insights-heading">
        <h2 id="insights-heading" className={styles.sectionTitle}>
          Kate · Voor jou
        </h2>
        {insightsState.isLoading && <Skeleton height={160} />}
        {insightsState.error && <ErrorState message={insightsState.error} />}
        {insightsState.data && <InsightCarousel insights={insightsState.data} />}
      </section>

      {accountsState.isLoading && (
        <div className={styles.section}>
          <Skeleton height={110} />
          <Skeleton height={110} />
        </div>
      )}

      {accountsState.error && <ErrorState message={accountsState.error} />}

      {accountsState.data && accounts.length === 0 && <EmptyState message="Je hebt nog geen rekeningen." />}

      {accountsState.data && accounts.length > 0 && (
        <>
          <AccountSection title="Zichtrekeningen" accounts={currentAccounts} layout={tileLayout} />
          <AccountSection title="Spaarrekeningen" accounts={savingsAccounts} layout={tileLayout} />
          <AccountSection
            title="Kredietkaarten en prepaidkaart"
            accounts={creditCardAccounts}
            layout={tileLayout}
            emptyMessage="Geen kredietkaart of prepaidkaart"
          />
        </>
      )}
    </div>
  );
}
