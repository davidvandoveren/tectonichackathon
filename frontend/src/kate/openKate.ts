/** Opens the Kate conversation from anywhere in the app (e.g. the desktop header button). */
export const OPEN_KATE_EVENT = "kate:open";

export function openKate(): void {
  window.dispatchEvent(new Event(OPEN_KATE_EVENT));
}
