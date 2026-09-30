import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InvestPage } from "./InvestPage";
import type { Overview } from "./investApi";

const base: Overview = {
  health: {
    status: "ready",
    savings: "18500.00",
    monthly_expenses: "2938.00",
    monthly_income: "3120.00",
    buffer: "8900.00",
    investable: "9600.00",
    notes: ["Je buffer van € 8,900 blijft altijd op je spaarrekening."],
  },
  answers: null,
  direction: null,
  catalog: [],
  plan: null,
  portfolio: { invested: "0.00", value: "0.00", holdings: [], drop_20_example: "8200" },
  tob_percent: "0.12",
  simulated: true,
};

const withDirection: Overview = {
  ...base,
  answers: { goal: "grow", horizon: "5to10", knowledge: "basic", drop_reaction: "wait" },
  direction: {
    profile: "neutral",
    shares_percent: 60,
    bonds_percent: 40,
    headline: "Je profiel: neutraal · ongeveer 60% aandelen, 40% obligaties",
    explanation: "Kate wijst een richting aan; jij kiest de ETF's.",
    warnings: [],
    suitable: true,
  },
};

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.restoreAllMocks());

describe("InvestPage", () => {
  it("starts with the buffer, asks, then points a direction without choosing for you", async () => {
    const posted: unknown[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      if (String(input).endsWith("/invest/answers")) {
        posted.push(JSON.parse(String(init?.body)));
        return Promise.resolve(json(withDirection));
      }
      return Promise.resolve(json(base));
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <InvestPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Buffer (blijft staan)")).toBeInTheDocument();
    expect(screen.getByText(/geen persoonlijk beleggingsadvies: jij kiest/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Verder" }));

    await user.click(screen.getByLabelText("Vermogen laten groeien"));
    await user.click(screen.getByLabelText("Over 5 tot 10 jaar"));
    await user.click(screen.getByLabelText("Ik weet wat een fonds of ETF is"));
    await user.click(screen.getByLabelText("Rustig afwachten"));
    await user.click(screen.getByRole("button", { name: "Toon mijn richting" }));

    expect(posted).toEqual([{ goal: "grow", horizon: "5to10", knowledge: "basic", drop_reaction: "wait" }]);
    expect(await screen.findByText(/ongeveer 60% aandelen/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bekijk ETF's die passen" })).toBeInTheDocument();
  });
});
