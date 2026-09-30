import { apiClient } from "./client";
import type { DemoUser, Me } from "./types";

export function getDemoUsers(signal?: AbortSignal): Promise<DemoUser[]> {
  return apiClient.get<DemoUser[]>("/auth/demo-users", signal);
}

export function login(username: string, password: string): Promise<Me> {
  return apiClient.post<Me>("/auth/login", { username, password });
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
