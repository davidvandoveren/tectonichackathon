/** Date helpers for nl-BE formatting and grouping transactions by booking date. */

export function greeting(hour: number = new Date().getHours()): string {
  if (hour < 12) {
    return "Goedemorgen";
  }
  if (hour < 18) {
    return "Goedemiddag";
  }
  return "Goedenavond";
}

export function formatDateLong(iso: string): string {
  return new Intl.DateTimeFormat("nl-BE", { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(iso)
  );
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Returns "Vandaag" / "Gisteren" for recent dates, otherwise a full localized date. */
export function formatDateGroup(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (isSameDay(date, today)) {
    return "Vandaag";
  }
  if (isSameDay(date, yesterday)) {
    return "Gisteren";
  }
  return formatDateLong(iso);
}

export interface DateGroup<T> {
  dateIso: string;
  items: T[];
}

/** Groups items by an ISO date key, preserving the original (API-provided) order within and across groups. */
export function groupByDate<T>(items: T[], getIso: (item: T) => string): DateGroup<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = getIso(item);
    const existing = groups.get(key);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(key, [item]);
    }
  }
  return Array.from(groups.entries()).map(([dateIso, groupItems]) => ({ dateIso, items: groupItems }));
}
