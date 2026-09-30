import { apiClient } from "../api/client";

export interface ArchetypeRow {
  archetype: string;
  label: string;
  customers: number;
  with_message: number;
  interrupted: number;
  silent: number;
  top_moments: string[];
}

export interface Population {
  size: number;
  with_message: number;
  interrupted: number;
  silent: number;
  nothing_at_all: number;
  held_back: number;
  by_moment: Record<string, number>;
  by_channel: Record<string, number>;
  silence_reasons: Record<string, number>;
  silence_labels: Record<string, string>;
  archetypes: ArchetypeRow[];
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  kbc_customers: number;
  full_bank_cpu_minutes: number;
}

export interface PersonaTrace {
  username: string;
  display_name: string;
  persona: string;
  signals: { type: string; evidence: string }[];
  moments: { type: string; urgency: string; confidence: string }[];
  actions: { title: string; channel: string; urgency: string; reason: string }[];
  silenced: { moment: string; reason_code: string; reason: string }[];
}

export interface Dashboard {
  today: string;
  population: Population;
  personas: PersonaTrace[];
}

export function getDashboard(size: number, signal?: AbortSignal): Promise<Dashboard> {
  return apiClient.get<Dashboard>(`/admin/dashboard?size=${size}`, signal);
}

export const MOMENT_LABELS: Record<string, string> = {
  cashflow_risk: "Saldo te krap voor vaste kosten",
  income_missing: "Verwacht inkomen blijft uit",
  first_salary: "Eerste loon",
  moving_house: "Verhuis",
  idle_savings: "Spaargeld staat stil",
  savings_habit_automatable: "Spaargewoonte automatiseren",
  deal_match: "Passende Kate Deal",
  card_package_gap: "Ontbrekende kaartverzekering",
  card_package_waste: "Betaalt voor ongebruikt kaartpakket",
};

export const CHANNEL_LABELS: Record<string, string> = {
  feed: "Kaartje in de app",
  push: "Pushmelding",
  sms: "Sms",
  call: "Telefoontje (AI, opt-in)",
};
