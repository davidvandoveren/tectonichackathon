import { useId } from "react";
import type { Account } from "../api/types";
import { AccountCard } from "./AccountCard";
import { EmptyAccountTile } from "./EmptyAccountTile";
import { SectionHeader } from "./SectionHeader";
import type { TileLayout } from "./TileViewToggle";
import styles from "./AccountSection.module.css";

interface AccountSectionProps {
  title: string;
  accounts: Account[];
  layout: TileLayout;
  /** When set, an empty section still renders with an outlined placeholder tile (e.g. credit cards). */
  emptyMessage?: string;
}

export function AccountSection({ title, accounts, layout, emptyMessage }: AccountSectionProps) {
  const headingId = useId();

  if (accounts.length === 0 && !emptyMessage) {
    return null;
  }

  return (
    <section className={styles.section} aria-labelledby={headingId}>
      <SectionHeader id={headingId} title={title} />
      <div className={layout === "grid" ? styles.grid : styles.list}>
        {accounts.map((account) => (
          <AccountCard key={account.id} account={account} layout={layout} />
        ))}
        {accounts.length === 0 && emptyMessage && <EmptyAccountTile message={emptyMessage} />}
      </div>
    </section>
  );
}
