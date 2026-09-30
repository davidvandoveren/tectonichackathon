/**
 * Kate Skills + consent API (see docs/api.md, "Kate Skills" and "Consent").
 * Money stays a 2-decimal string end to end; amounts are never computed in the browser.
 */
import { apiClient } from "../api/client";
import type { Insight } from "../api/types";

export type Level = "off" | "suggest" | "prepare" | "auto";
export type Risk = "info" | "internal_money" | "external_money" | "product_change" | "regulated";

export interface Mandate {
  max_per_execution: string;
  max_per_month: string;
}

export interface SkillAction {
  id: string;
  title: string;
  description: string;
  risk: Risk;
  level: Level;
  max_level: Level;
  mandate: Mandate | null;
}

export interface Skill {
  id: string;
  title: string;
  description: string;
  actions: SkillAction[];
}

export interface FeedAction {
  moment: string;
  action: string;
  title: string;
  summary: string;
  level: Level;
  can_confirm: boolean;
}

export interface Outcome {
  kind: "done" | "navigate" | "advisor_handoff";
  message: string;
  navigate_to: string | null;
  handoff_summary: string | null;
}

export interface Proposal {
  id: string;
  action: string;
  summary: string;
  reason: string;
  status: "suggested" | "pending" | "executed" | "failed" | "declined" | "expired";
  outcome: Outcome | null;
}

export interface ActivityEntry {
  at: string;
  event: string;
  action: string;
  summary: string;
  source: string | null;
  reason: string | null;
}

export type DataConsent = Record<string, boolean>;

export const LEVELS: Level[] = ["off", "suggest", "prepare", "auto"];

export const getFeedActions = (signal?: AbortSignal) =>
  apiClient.get<FeedAction[]>("/skills/feed-actions", signal);

export const proposeFromMoment = (moment: string) =>
  apiClient.post<Proposal>("/proposals/from-moment", { moment });

export const approveProposal = (id: string) =>
  apiClient.post<Proposal>(`/proposals/${encodeURIComponent(id)}/approve`, {});

export const dismissMoment = (moment: string) =>
  apiClient.post<undefined>(`/kate/feed/${encodeURIComponent(moment)}/dismiss`, {});

export const getSkills = (signal?: AbortSignal) => apiClient.get<Skill[]>("/skills", signal);

export const setActionConsent = (actionId: string, level: Level, mandate: Mandate | null) =>
  apiClient.put<SkillAction>(`/skills/consent/${encodeURIComponent(actionId)}`, {
    level,
    ...(mandate ? { mandate } : {}),
  });

export const getDataConsent = (signal?: AbortSignal) =>
  apiClient.get<DataConsent>("/kate/consent", signal);

export const setDataConsent = (domain: string, allowed: boolean) =>
  apiClient.put<DataConsent>("/kate/consent", { domain, allowed });

export const getActivity = (signal?: AbortSignal) =>
  apiClient.get<ActivityEntry[]>("/activity", signal);

/**
 * The engine's moment type for an insight card. Newer backends send `moment`; older ones only
 * have ids like `i_first_salary_u_emma`.
 */
export function momentOf(insight: Insight): string | undefined {
  if (insight.moment) return insight.moment;
  return /^i_(.+)_u_[a-z0-9]+$/.exec(insight.id)?.[1];
}
