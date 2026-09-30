import { apiClient } from "../api/client";

/** Where Kate delivers a message; see "Kate feed" in docs/api.md. */
export type Channel = "feed" | "push" | "sms" | "call" | "none";

export interface FeedItem {
  id: string;
  title: string;
  body: string;
  urgency: number;
  channel: Channel;
  reason: string;
  cta_label: string;
  cta_target: string;
  requires_advisor: boolean;
}

/** Something Kate noticed and deliberately did not say. */
export interface Silence {
  moment: string;
  reason_code: string;
  reason: string;
}

export interface KateFeed {
  items: FeedItem[];
  silenced: Silence[];
}

export type Scenario = "none" | "salary_paid" | "salary_missing";

export interface TimeMachineResult {
  days_shifted: number;
  clock_offset_days: number;
  today: string;
  username: string;
  injected: number;
  feed: KateFeed;
}

/** Bands from docs/api.md: they never overlap, so a risk can never be outranked by a nudge. */
export function bandOf(urgency: number): "risk" | "obligation" | "opportunity" {
  if (urgency >= 70) return "risk";
  if (urgency >= 40) return "obligation";
  return "opportunity";
}

export const INTERRUPTIVE: ReadonlySet<string> = new Set(["push", "sms", "call"]);

export const getKateFeed = (signal?: AbortSignal) => apiClient.get<KateFeed>("/kate/feed", signal);

/** Demo only: the backend answers 404 to anyone who is not a configured admin. */
export const runTimeMachine = (days: number, scenario: Scenario) =>
  apiClient.post<TimeMachineResult>("/admin/time-machine", { days, scenario });
