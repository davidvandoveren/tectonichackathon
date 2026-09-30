import { apiClient } from "./client";
import type { Me } from "./types";

export function getMe(signal?: AbortSignal): Promise<Me> {
  return apiClient.get<Me>("/me", signal);
}
