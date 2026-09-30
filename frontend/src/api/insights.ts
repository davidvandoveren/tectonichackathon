import { apiClient } from "./client";
import type { Insight } from "./types";

export function getInsights(signal?: AbortSignal): Promise<Insight[]> {
  return apiClient.get<Insight[]>("/insights", signal);
}
