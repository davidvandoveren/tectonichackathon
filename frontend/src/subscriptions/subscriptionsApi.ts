import { apiClient } from "../api/client";

export type SubscriptionFlag = "price_increase" | "duplicate" | "trial_converted";
export type SubscriptionStatus = "unknown" | "in_use" | "cancel_reminder";

export interface Subscription {
  id: string;
  name: string;
  group: string | null;
  amount: string;
  previous_amount: string | null;
  yearly_cost: string;
  frequency: "monthly";
  first_seen: string;
  last_charged: string;
  next_expected: string;
  flags: SubscriptionFlag[];
  duplicate_of: string[];
  reason: string;
  status: SubscriptionStatus;
  remind_on: string | null;
}

export interface SubscriptionsOverview {
  subscriptions: Subscription[];
  monthly_total: string;
  yearly_total: string;
  yearly_savings: string;
  hidden_sensitive: number;
}

export function getSubscriptions(signal?: AbortSignal): Promise<SubscriptionsOverview> {
  return apiClient.get<SubscriptionsOverview>("/subscriptions", signal);
}

export function sendSubscriptionFeedback(
  id: string,
  feedback: { still_used: boolean; remind_to_cancel?: boolean }
): Promise<Subscription> {
  return apiClient.post<Subscription>(`/subscriptions/${encodeURIComponent(id)}/feedback`, feedback);
}

export const GROUP_LABELS: Record<string, string> = {
  streaming: "Streaming",
  muziek: "Muziek",
  cloudopslag: "Cloudopslag",
  fitness: "Fitness",
  telecom: "Telecom",
};
