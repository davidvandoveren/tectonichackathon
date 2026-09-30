import { apiClient } from "./client";
import type { Transaction, TransferRequest } from "./types";

export function createTransfer(payload: TransferRequest): Promise<Transaction> {
  return apiClient.post<Transaction>("/transfers", payload);
}
