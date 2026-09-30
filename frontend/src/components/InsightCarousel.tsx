import type { Insight } from "../api/types";
import { InsightCard } from "./InsightCard";
import { EmptyState } from "./EmptyState";
import styles from "./InsightCarousel.module.css";

interface InsightCarouselProps {
  insights: Insight[];
}

export function InsightCarousel({ insights }: InsightCarouselProps) {
  if (insights.length === 0) {
    return <EmptyState message="Nog geen persoonlijke inzichten. Kom later terug." />;
  }

  return (
    <ul className={styles.track} aria-label="Voor jou">
      {insights.map((insight) => (
        <li key={insight.id} className={styles.item}>
          <InsightCard insight={insight} />
        </li>
      ))}
    </ul>
  );
}
