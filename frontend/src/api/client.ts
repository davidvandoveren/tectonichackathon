/**
 * Small typed fetch wrapper for the `/api/v1` backend.
 * - Session is an HttpOnly cookie; we never read or store a token.
 * - Every state-changing request sends `Content-Type: application/json`.
 * - Any 401 response notifies subscribers so the app can route to /login.
 */
import { sessionSlot } from "../lib/sessionSlot";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type UnauthorizedListener = () => void;

const unauthorizedListeners = new Set<UnauthorizedListener>();

/** Subscribe to global 401 events (e.g. to clear auth state and redirect to /login). */
export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

function notifyUnauthorized(): void {
  for (const listener of unauthorizedListeners) {
    listener();
  }
}

type HttpMethod = "GET" | "POST" | "PUT";

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  signal?: AbortSignal;
}

function isErrorBody(value: unknown): value is { detail: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    typeof (value as { detail: unknown }).detail === "string"
  );
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (sessionSlot) {
    headers["X-Session-Slot"] = sessionSlot;
  }
  const init: RequestInit = {
    method,
    credentials: "same-origin",
    headers,
    signal,
  };

  // Every state-changing request is JSON, even without a body (e.g. logout): the backend's CSRF
  // guard rejects anything else, and some proxies require a Content-Length on POST.
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body ?? {});
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Geen verbinding met de server. Controleer je internetverbinding.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json") ? await response.json() : undefined;

  if (!response.ok) {
    const detail = isErrorBody(payload) ? payload.detail : response.statusText || "Er ging iets mis.";
    if (response.status === 401) {
      notifyUnauthorized();
    }
    throw new ApiError(response.status, detail);
  }

  return payload as T;
}

export const apiClient = {
  get: <T>(path: string, signal?: AbortSignal): Promise<T> => request<T>(path, { method: "GET", signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> =>
    request<T>(path, { method: "POST", body, signal }),
  put: <T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> =>
    request<T>(path, { method: "PUT", body, signal }),
};
