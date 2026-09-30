import { useEffect, useState } from "react";
import { getKateFeed, type KateFeed } from "./momentsApi";

const EMPTY: KateFeed = { items: [], silenced: [] };

/** The Kate feed for the extras on home. Optional: on any error home simply shows nothing extra. */
export function useKateFeed(): KateFeed {
  const [feed, setFeed] = useState<KateFeed>(EMPTY);

  useEffect(() => {
    const controller = new AbortController();
    getKateFeed(controller.signal)
      .then(setFeed)
      .catch(() => setFeed(EMPTY));
    return () => controller.abort();
  }, []);

  return feed;
}
