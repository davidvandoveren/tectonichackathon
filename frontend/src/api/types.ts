/**
 * Types mirroring the API contract in `docs/api.md`.
 * Money is always a decimal string ("1234.50"), never a float.
 * Dates are ISO 8601 strings, kept as `string` and formatted at the edge (see src/lib/dates.ts).
 */

export interface DemoUser {
  username: string;
  display_name: string;
  persona: string;
}

export interface AuthConfig {
  passwordless_login: boolean;
}

export interface Me {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  persona: string;
}

export type AccountType = "current" | "savings" | "credit_card";

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  iban: string;
  balance: string;
  currency: string;
}

export type TransactionCategory =
  | "income"
  | "groceries"
  | "housing"
  | "transport"
  | "leisure"
  | "shopping"
  | "utilities"
  | "savings"
  | "transfer"
  | "other";

export interface Transaction {
  id: string;
  account_id: string;
  booked_at: string;
  description: string;
  counterparty: string;
  amount: string;
  currency: string;
  category: TransactionCategory;
}

export interface Insight {
  id: string;
  kind: string;
  title: string;
  body: string;
  cta_label: string;
  cta_target: string;
  reason: string;
}

export interface TransferRequest {
  from_account_id: string;
  to_iban: string;
  to_name: string;
  amount: string;
  description: string;
}
