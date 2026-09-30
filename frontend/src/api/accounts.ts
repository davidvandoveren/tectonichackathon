import { apiClient } from "./client";
import type { Account, Transaction } from "./types";

export function getAccounts(signal?: AbortSignal): Promise<Account[]> {
  return apiClient.get<Account[]>("/accounts", signal);
}

export function getAccount(accountId: string, signal?: AbortSignal): Promise<Account> {
  return apiClient.get<Account>(`/accounts/${encodeURIComponent(accountId)}`, signal);
}

export function getTransactions(accountId: string, limit = 50, signal?: AbortSignal): Promise<Transaction[]> {
  return apiClient.get<Transaction[]>(
    `/accounts/${encodeURIComponent(accountId)}/transactions?limit=${limit}`,
    signal
  );
}
