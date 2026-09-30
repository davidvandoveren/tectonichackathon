import type { Insight } from "../api/types";
import { momentOf, type FeedAction } from "../skills/skillsApi";
import { InsightCard } from "./InsightCard";
import { EmptyState } from "./EmptyState";
import styles from "./InsightCarousel.module.css";

interface InsightCarouselProps {
  insights: Insight[];
  /** Kate Skills actions keyed by moment type (see GET /skills/feed-actions). */
  actions?: Record<string, FeedAction>;
  onDismissed?: (insightId: string) => void;
}

export function InsightCarousel({ insights, actions = {}, onDismissed }: InsightCarouselProps) {
  if (insights.length === 0) {
    return <EmptyState message="Nog geen persoonlijke inzichten. Kom later terug." />;
  }

  return (
    <ul className={styles.track} aria-label="Voor jou">
      {insights.map((insight) => (
        <li key={insight.id} className={styles.item}>
          <InsightCard
            insight={insight}
            action={actions[momentOf(insight) ?? ""]}
            onDismissed={() => onDismissed?.(insight.id)}
          />
        </li>
      ))}
    </ul>
  );
}
