import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KateConsentPage } from "./KateConsentPage";
import type { ActivityEntry, Skill } from "./skillsApi";

const skills: Skill[] = [
  {
    id: "savings",
    title: "Sparen",
    description: "…",
    actions: [
      {
        id: "savings.move_to_savings",
        title: "Geld opzij zetten",
        description: "…",
        risk: "internal_money",
        level: "prepare",
        max_level: "auto",
        mandate: null,
      },
    ],
  },
  {
    id: "payments",
    title: "Betalen",
    description: "…",
    actions: [
      {
        id: "payments.transfer",
        title: "Overschrijving voorbereiden",
        description: "…",
        risk: "external_money",
        level: "prepare",
        max_level: "prepare",
        mandate: null,
      },
    ],
  },
];

const activity: ActivityEntry[] = [
  { at: "2026-09-30T19:00:00Z", event: "executed", action: "savings.create_goal", summary: "Spaardoel 'Buffer' van € 5 955,00", source: "moment", reason: "…" },
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function mockApi() {
  const puts: { url: string; body: unknown }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (init?.method === "PUT") {
      const body: unknown = JSON.parse(String(init.body));
      puts.push({ url, body });
      if (url.endsWith("/kate/consent")) {
        return Promise.resolve(json({ income: true, spending: false, balances: true, products: true }));
      }
      const b = body as { level: string; mandate?: unknown };
      return Promise.resolve(json({ ...skills[0].actions[0], level: b.level, mandate: b.mandate ?? null }));
    }
    if (url.endsWith("/kate/consent")) {
      return Promise.resolve(json({ income: true, spending: true, balances: true, products: true }));
    }
    if (url.endsWith("/skills")) return Promise.resolve(json(skills));
    return Promise.resolve(json(activity));
  });
  return puts;
}

function renderPage() {
  render(
    <MemoryRouter>
      <KateConsentPage />
    </MemoryRouter>
  );
}

afterEach(() => vi.restoreAllMocks());

describe("KateConsentPage", () => {
  it("switching off a data domain tells the server immediately", async () => {
    const puts = mockApi();
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("checkbox", { name: /Uitgaven/ }));
    expect(puts).toContainEqual({ url: "/api/v1/kate/consent", body: { domain: "spending", allowed: false } });
    expect(screen.getByRole("checkbox", { name: /Uitgaven/ })).not.toBeChecked();
  });

  it("only offers levels up to what the action allows", async () => {
    mockApi();
    renderPage();
    const transfer = await screen.findByRole("group", { name: "Overschrijving voorbereiden" });
    expect(within(transfer).queryByRole("radio", { name: "Automatisch" })).not.toBeInTheDocument();
    const saving = screen.getByRole("group", { name: "Geld opzij zetten" });
    expect(within(saving).getByRole("radio", { name: "Automatisch" })).toBeInTheDocument();
  });

  it("automatic money moves need a mandate before anything is saved", async () => {
    const puts = mockApi();
    const user = userEvent.setup();
    renderPage();
    const saving = await screen.findByRole("group", { name: "Geld opzij zetten" });
    await user.click(within(saving).getByRole("radio", { name: "Automatisch" }));
    expect(puts).toEqual([]);
    await user.clear(within(saving).getByLabelText("Max. per keer (€)"));
    await user.type(within(saving).getByLabelText("Max. per keer (€)"), "50");
    await user.click(within(saving).getByRole("button", { name: "Mandaat opslaan" }));
    expect(puts).toContainEqual({
      url: "/api/v1/skills/consent/savings.move_to_savings",
      body: { level: "auto", mandate: { max_per_execution: "50.00", max_per_month: "200.00" } },
    });
  });

  it("lowering a level saves straight away", async () => {
    const puts = mockApi();
    const user = userEvent.setup();
    renderPage();
    const saving = await screen.findByRole("group", { name: "Geld opzij zetten" });
    await user.click(within(saving).getByRole("radio", { name: "Uit" }));
    expect(puts).toContainEqual({ url: "/api/v1/skills/consent/savings.move_to_savings", body: { level: "off" } });
  });

  it("shows what Kate did", async () => {
    mockApi();
    renderPage();
    expect(await screen.findByText("Spaardoel 'Buffer' van € 5 955,00")).toBeInTheDocument();
    expect(screen.getByText("Uitgevoerd")).toBeInTheDocument();
  });
});
