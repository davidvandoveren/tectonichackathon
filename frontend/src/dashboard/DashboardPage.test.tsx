import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { Dashboard } from "./dashboardApi";

const dashboard: Dashboard = {
  today: "2026-09-30",
  population: {
    size: 10000,
    with_message: 5470,
    interrupted: 1053,
    silent: 4530,
    nothing_at_all: 4257,
    held_back: 273,
    by_moment: { idle_savings: 1439, income_missing: 308 },
    by_channel: { feed: 5018, push: 635, sms: 163, call: 255 },
    silence_reasons: { low_confidence: 414 },
    silence_labels: { low_confidence: "Te onzeker om iets te zeggen." },
    archetypes: [
      { archetype: "salary_missing", label: "Loon blijft uit", customers: 308, with_message: 308, interrupted: 308, silent: 0, top_moments: ["income_missing"] },
    ],
    p50_ms: 0.7,
    p95_ms: 1.04,
    p99_ms: 1.5,
    kbc_customers: 2300000,
    full_bank_cpu_minutes: 28.1,
  },
  personas: [
    {
      username: "jan",
      display_name: "Jan Maes",
      persona: "Bediende",
      signals: [{ type: "deposit_like_outflow", evidence: "Huurwaarborg van € 1.900,00." }],
      moments: [{ type: "moving_house", urgency: "obligation", confidence: "0.82" }],
      actions: [{ title: "Ga je verhuizen?", channel: "push", urgency: "70", reason: "Huurwaarborg en meubelen." }],
      silenced: [],
    },
  ],
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.restoreAllMocks());

describe("DashboardPage", () => {
  it("leads with deliberate silence and shows the trace per persona", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(dashboard));
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(await screen.findByText("Kregen bewust niets")).toBeInTheDocument();
    expect(screen.getAllByText("45,3%").length).toBeGreaterThan(0);
    expect(screen.getByText("Huurwaarborg van € 1.900,00.")).toBeInTheDocument();
    expect(screen.getByText("Ga je verhuizen?")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("tells non-admins it is not for them", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: "Not found" }, 404));
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("alleen voor de demo-beheerder");
  });
});
