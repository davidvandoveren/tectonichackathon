import { apiClient } from "../api/client";

export type NotificationChannel = "feed" | "push" | "sms" | "call";

export interface KateNotification {
  id: string;
  source: string;
  title: string;
  body: string;
  reason: string;
  channel: NotificationChannel;
  cta_label: string;
  cta_target: string;
  sent_on: string;
  created_at: string;
  read: boolean;
}

export interface Inbox {
  unread: number;
  items: KateNotification[];
}

export const INTERRUPTIVE: ReadonlySet<NotificationChannel> = new Set(["push", "sms", "call"]);

export function getInbox(signal?: AbortSignal): Promise<Inbox> {
  return apiClient.get<Inbox>("/kate/notifications", signal);
}

export function markRead(id: string): Promise<KateNotification> {
  return apiClient.post<KateNotification>(`/kate/notifications/${encodeURIComponent(id)}/read`, {});
}

export function markAllRead(): Promise<undefined> {
  return apiClient.post<undefined>("/kate/notifications/read-all", {});
}

/** Tells every bell on the page to refresh now (after reading or after an action). */
export function refreshNotifications(): void {
  window.dispatchEvent(new Event("kate-notifications-refresh"));
}
