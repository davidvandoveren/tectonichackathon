import { apiClient } from "../api/client";

export type ShareLevel = "exists" | "gift" | "pot" | "balances";
export type Role =
  | "partner"
  | "parent"
  | "child"
  | "grandparent"
  | "grandchild"
  | "godparent"
  | "godchild"
  | "sibling"
  | "other";

export interface Guardianship {
  my_side: "guardian" | "ward";
  active: boolean;
  ends_on: string;
}

export interface FamilyLink {
  id: string;
  status: "pending" | "active";
  direction: "incoming" | "outgoing" | null;
  other_name: string;
  my_role: Role;
  their_role: Role;
  i_share: ShareLevel;
  they_share: ShareLevel;
  guardianship: Guardianship | null;
  can_end: boolean;
  can_view_accounts: boolean;
  since: string;
}

export interface PotContribution {
  name: string;
  amount: string;
  booked_on: string;
  mine: boolean;
}

export interface Pot {
  id: string;
  name: string;
  goal: string | null;
  balance: string;
  progress_percent: number | null;
  owner_name: string;
  mine: boolean;
  access: "owner" | "pot" | "gift";
  members: string[] | null;
  contributions: PotContribution[];
}

export interface FamilySuggestion {
  id: string;
  kind: string;
  title: string;
  body: string;
  reason: string;
  cta_label: string;
  cta_target: string;
}

export interface FamilyOverview {
  me: { minor: boolean; adult_on: string | null };
  links: FamilyLink[];
  pots: Pot[];
  suggestions: FamilySuggestion[];
}

export interface SharedAccount {
  name: string;
  type: "current" | "savings" | "credit_card";
  balance: string;
  currency: string;
}

const link = (id: string) => `/family/links/${encodeURIComponent(id)}`;

export const getFamily = (signal?: AbortSignal) =>
  apiClient.get<FamilyOverview>("/family", signal);

export const invite = (body: {
  username: string;
  my_role: Role;
  share: ShareLevel;
}) =>
  apiClient.post<{ message: string; link: FamilyLink }>(
    "/family/invites",
    body,
  );

export const acceptLink = (id: string, share: ShareLevel) =>
  apiClient.post<FamilyLink>(`${link(id)}/accept`, { share });

export const endLink = (id: string) =>
  apiClient.post<undefined>(`${link(id)}/end`, {});

export const setSharing = (id: string, share: ShareLevel) =>
  apiClient.post<FamilyLink>(`${link(id)}/sharing`, { share });

export const getSharedAccounts = (id: string) =>
  apiClient.get<SharedAccount[]>(`${link(id)}/accounts`);

export const createPot = (body: {
  name: string;
  goal: string | null;
  member_link_ids: string[];
}) => apiClient.post<Pot>("/family/pots", body);

export const contribute = (
  potId: string,
  body: { from_account_id: string; amount: string; note: string },
) =>
  apiClient.post<Pot>(
    `/family/pots/${encodeURIComponent(potId)}/contributions`,
    body,
  );

export const SHARE_LABELS: Record<ShareLevel, string> = {
  exists: "Alleen dat we gekoppeld zijn",
  gift: "Mag bijdragen aan potjes die ik deel",
  pot: "Ziet mijn potjes en wie wat gaf",
  balances: "Ziet ook mijn saldo's (alleen lezen)",
};

export const ROLE_LABELS: Record<Role, string> = {
  partner: "Partner",
  parent: "Ouder",
  child: "Kind",
  grandparent: "Grootouder",
  grandchild: "Kleinkind",
  godparent: "Meter of peter",
  godchild: "Petekind",
  sibling: "Broer of zus",
  other: "Familie of vriend",
};
