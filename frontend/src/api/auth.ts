import { apiClient } from "./client";
import type { AuthConfig, DemoUser, Me } from "./types";

export function getDemoUsers(signal?: AbortSignal): Promise<DemoUser[]> {
  return apiClient.get<DemoUser[]>("/auth/demo-users", signal);
}

export function getAuthConfig(signal?: AbortSignal): Promise<AuthConfig> {
  return apiClient.get<AuthConfig>("/auth/config", signal);
}

export function demoLogin(username: string): Promise<Me> {
  return apiClient.post<Me>("/auth/demo-login", { username });
}

export function login(username: string, password: string): Promise<Me> {
  return apiClient.post<Me>("/auth/login", { username, password });
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
