import { apiClient } from "../api/client";

export type Goal = "grow" | "pension" | "purchase" | "income";
export type Horizon = "lt3" | "3to5" | "5to10" | "gt10";
export type Knowledge = "none" | "basic" | "experienced";
export type Reaction = "sell_all" | "worried" | "wait" | "buy_more";

export interface Answers {
  goal: Goal;
  horizon: Horizon;
  knowledge: Knowledge;
  drop_reaction: Reaction;
}

export interface Health {
  status: "ready" | "caution" | "build_buffer";
  savings: string;
  monthly_expenses: string;
  monthly_income: string;
  buffer: string;
  investable: string;
  notes: string[];
}

export interface Direction {
  profile: "defensive" | "neutral" | "dynamic";
  shares_percent: number;
  bonds_percent: number;
  headline: string;
  explanation: string;
  warnings: string[];
  suitable: boolean;
}

export interface Etf {
  id: string;
  name: string;
  index: string;
  asset_class: "shares" | "bonds";
  role: "core" | "satellite" | "niche" | "complex";
  region: string;
  ter_percent: string;
  risk_class: number;
  distributing: boolean;
  holdings: number;
  explanation: string;
  price: string;
  fit: "fits" | "addition" | "caution" | "not_for_you" | null;
  fit_note: string | null;
  allowed: boolean;
}

export interface MixCheck {
  shares_percent: number;
  yearly_cost_percent: string;
  warnings: string[];
  blocked: string[];
  needs_acknowledgement: boolean;
}

export interface Plan {
  status: "active" | "paused" | "stopped" | "completed";
  weights: Record<string, number>;
  total: string;
  months: number;
  monthly: string;
  invested: string;
  next_on: string | null;
  buffer: string;
  pause_reason: string | null;
  steps: { number: number; on: string; amount: string; tax: string }[];
}

export interface Overview {
  health: Health;
  answers: Answers | null;
  direction: Direction | null;
  catalog: Etf[];
  plan: Plan | null;
  portfolio: {
    invested: string;
    value: string;
    holdings: { etf_id: string; name: string; units: string; invested: string; value: string }[];
    drop_20_example: string;
  };
  tob_percent: string;
  simulated: boolean;
}

export const getOverview = (signal?: AbortSignal) => apiClient.get<Overview>("/invest", signal);

export const sendAnswers = (answers: Answers) => apiClient.post<Overview>("/invest/answers", answers);

export const checkMix = (weights: Record<string, number>, signal?: AbortSignal) =>
  apiClient.post<MixCheck>("/invest/check", { weights }, signal);

export const startPlan = (body: {
  weights: Record<string, number>;
  total: string;
  months: number;
  accept_risks: boolean;
}) => apiClient.post<Overview>("/invest/plan", body);

export const changePlan = (action: "pause" | "resume" | "stop") =>
  apiClient.post<Overview>(`/invest/plan/${action}`, {});
