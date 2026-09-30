import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FamilyPage } from "./FamilyPage";
import type { FamilyLink, FamilyOverview } from "./familyApi";

function link(overrides: Partial<FamilyLink>): FamilyLink {
  return {
    id: "fl_000000000001",
    status: "active",
    direction: null,
    other_name: "Noor Maes",
    my_role: "parent",
    their_role: "child",
    i_share: "exists",
    they_share: "balances",
    guardianship: { my_side: "guardian", active: true, ends_on: "2026-10-21" },
    can_end: false,
    can_view_accounts: true,
    since: "2008-10-21",
    ...overrides,
  };
}

const overview: FamilyOverview = {
  me: { minor: false, adult_on: null },
  links: [
    link({}),
    link({
      id: "fl_000000000002",
      status: "pending",
      direction: "incoming",
      other_name: "Lucas Janssens",
      my_role: "other",
      their_role: "other",
      they_share: "gift",
      guardianship: null,
      can_end: true,
      can_view_accounts: false,
    }),
  ],
  pots: [
    {
      id: "fp_000000000001",
      name: "Ons trouwfeest",
      goal: "8000.00",
      balance: "2500.00",
      progress_percent: 31,
      owner_name: "Emma Peeters",
      mine: false,
      access: "gift",
      members: null,
      contributions: [],
    },
  ],
  suggestions: [
    {
      id: "guardianship-ends-fl_000000000001",
      kind: "guardianship_ending",
      title: "Noor wordt over 21 dagen 18",
      body: "Dan stopt je wettelijke toegang.",
      reason: "Die voogdij loopt volgens de wet af op de 18de verjaardag.",
      cta_label: "Bekijk familiekring",
      cta_target: "/family",
    },
  ],
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => vi.restoreAllMocks());

describe("FamilyPage", () => {
  it("shows the circle, explains why, and accepts an invite with a chosen share", async () => {
    const posted: unknown[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/accept")) {
        posted.push(JSON.parse(String(init?.body)));
        return Promise.resolve(json(link({ id: "fl_000000000002" })));
      }
      if (url.endsWith("/accounts")) return Promise.resolve(json([]));
      return Promise.resolve(json(overview));
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <FamilyPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("Noor wordt over 21 dagen 18"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Wettelijke voogdij tot/)).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Ons trouwfeest: 31%" }),
    ).toBeInTheDocument();
    // A guardian cannot end the link while the child is a minor.
    expect(
      screen.queryByRole("button", { name: "Link stopzetten" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Waarom zie ik dit/ }));
    expect(screen.getByText(/loopt volgens de wet af/)).toBeInTheDocument();

    const [inviteShare] = screen.getAllByLabelText("Wat deel jij?");
    await user.selectOptions(inviteShare, "gift");
    await user.click(screen.getByRole("button", { name: "Ja, koppel ons" }));
    expect(posted).toEqual([{ share: "gift" }]);
  });

  it("shows the server's message after an invite, whoever it went to", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (String(input).endsWith("/family/invites")) {
        return Promise.resolve(
          json(
            {
              message: "Als deze persoon een KBC-klant is...",
              link: link({ direction: "outgoing" }),
            },
            202,
          ),
        );
      }
      if (String(input).endsWith("/accounts")) return Promise.resolve(json([]));
      return Promise.resolve(json({ ...overview, links: [], suggestions: [] }));
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <FamilyPage />
      </MemoryRouter>,
    );
    await user.type(await screen.findByLabelText("Gebruikersnaam"), "iemand");
    await user.click(
      screen.getByRole("button", { name: "Verstuur uitnodiging" }),
    );
    expect(
      await screen.findByText("Als deze persoon een KBC-klant is..."),
    ).toBeInTheDocument();
  });
});
