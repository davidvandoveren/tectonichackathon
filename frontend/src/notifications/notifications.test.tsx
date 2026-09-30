import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NotificationBell } from "./NotificationBell";
import { NotificationsPage } from "./NotificationsPage";
import type { Inbox, KateNotification } from "./notificationsApi";

function note(overrides: Partial<KateNotification>): KateNotification {
  return {
    id: "nt_000000000001",
    source: "invest",
    title: "Kate zette je beleggingsplan op pauze",
    body: "Stap 2 zou je buffer aanspreken.",
    reason: "Kate belegt nooit geld uit je buffer.",
    channel: "push",
    cta_label: "Bekijk je beleggingen",
    cta_target: "/invest",
    sent_on: "2026-10-01",
    created_at: "2026-10-01T10:00:00",
    read: false,
    ...overrides,
  };
}

const inbox: Inbox = {
  unread: 2,
  items: [note({}), note({ id: "nt_000000000002", source: "moment", channel: "feed", title: "Ga je verhuizen?" })],
};

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

describe("Kate notifications", () => {
  it("shows the unread count and a toast for a new push", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => Promise.resolve(json(inbox)));
    render(
      <MemoryRouter initialEntries={["/transfer"]}>
        <NotificationBell variant="mobile" />
      </MemoryRouter>
    );
    expect(await screen.findByRole("button", { name: "Meldingen van Kate, 2 ongelezen" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Kate zette je beleggingsplan op pauze");
  });

  it("lists what Kate sent and explains why", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => Promise.resolve(json(inbox)));
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    expect(await screen.findByText("Ga je verhuizen?")).toBeInTheDocument();
    expect(screen.getByText("2 ongelezen")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: /Waarom kreeg ik dit/ })[0]);
    expect(screen.getByText("Kate belegt nooit geld uit je buffer.")).toBeInTheDocument();
  });
});
