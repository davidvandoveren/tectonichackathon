import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SubscriptionsPage } from "./SubscriptionsPage";
import type { Subscription, SubscriptionsOverview } from "./subscriptionsApi";

function sub(overrides: Partial<Subscription>): Subscription {
  return {
    id: "sub_000000000001",
    name: "Netflix",
    group: "streaming",
    amount: "13.49",
    previous_amount: null,
    yearly_cost: "161.88",
    frequency: "monthly",
    first_seen: "2026-07-01",
    last_charged: "2026-09-26",
    next_expected: "2026-10-26",
    flags: ["duplicate"],
    duplicate_of: ["Disney+"],
    reason: "We weten niet of je het gebruikt.",
    status: "unknown",
    remind_on: null,
    ...overrides,
  };
}

const overview: SubscriptionsOverview = {
  subscriptions: [
    sub({}),
    sub({ id: "sub_000000000002", name: "Disney+", amount: "10.99", yearly_cost: "131.88", duplicate_of: ["Netflix"] }),
  ],
  monthly_total: "24.48",
  yearly_total: "293.76",
  yearly_savings: "0.00",
  hidden_sensitive: 1,
};

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.restoreAllMocks());

describe("SubscriptionsPage", () => {
  it("points out duplicates and asks instead of guessing usage", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      if (String(input).endsWith("/feedback")) {
        expect(JSON.parse(String(init?.body))).toEqual({ still_used: false, remind_to_cancel: true });
        return Promise.resolve(
          json(sub({ id: "sub_000000000002", name: "Disney+", status: "cancel_reminder", remind_on: "2026-10-18" }))
        );
      }
      return Promise.resolve(json(overview));
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SubscriptionsPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Je betaalt voor 2 streamingdiensten")).toBeInTheDocument();
    expect(screen.getAllByText("Gebruik je dit nog?")).toHaveLength(2);
    expect(screen.getByText(/1 betaling analyseren we bewust niet/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Nee, herinner me om op te zeggen" })[1]);
    expect(await screen.findByText(/We herinneren je op/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("bespaar je");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
