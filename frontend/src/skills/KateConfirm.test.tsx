import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KateConfirm } from "./KateConfirm";
import type { FeedAction, Proposal } from "./skillsApi";

const action: FeedAction = {
  moment: "first_salary",
  action: "savings.create_goal",
  title: "Spaardoel maken",
  summary: "Spaardoel 'Buffer' van € 5 955,00",
  level: "prepare",
  can_confirm: true,
};

function proposal(overrides: Partial<Proposal>): Proposal {
  return {
    id: "p_1",
    action: "savings.create_goal",
    summary: action.summary,
    reason: "…",
    status: "pending",
    outcome: null,
    ...overrides,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderConfirm(props: Partial<Parameters<typeof KateConfirm>[0]> = {}) {
  const onDismissed = vi.fn();
  render(
    <MemoryRouter>
      <KateConfirm action={action} onDismissed={onDismissed} {...props} />
    </MemoryRouter>
  );
  return { onDismissed };
}

afterEach(() => vi.restoreAllMocks());

describe("KateConfirm", () => {
  it("shows exactly what Kate will do before anything happens", () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    renderConfirm();
    expect(screen.getByText(action.summary)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bevestig" })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("confirm = create from the moment, then approve, then show the result", async () => {
    const calls: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      calls.push(`${init?.method} ${url}`);
      if (url.endsWith("/proposals/from-moment")) {
        expect(JSON.parse(String(init?.body))).toEqual({ moment: "first_salary" });
        return Promise.resolve(json(proposal({}), 201));
      }
      return Promise.resolve(
        json(
          proposal({
            status: "executed",
            outcome: { kind: "done", message: "Spaardoel 'Buffer' aangemaakt.", navigate_to: null, handoff_summary: null },
          })
        )
      );
    });
    const user = userEvent.setup();
    renderConfirm();
    await user.click(screen.getByRole("button", { name: "Bevestig" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Spaardoel 'Buffer' aangemaakt.");
    expect(calls).toEqual(["POST /api/v1/proposals/from-moment", "POST /api/v1/proposals/p_1/approve"]);
    expect(screen.queryByRole("button", { name: "Bevestig" })).not.toBeInTheDocument();
  });

  it("does not approve again when Kate already acted within the customer's mandate", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(
        proposal({
          status: "executed",
          outcome: { kind: "done", message: "€ 40,00 staat op je spaarrekening.", navigate_to: null, handoff_summary: null },
        }),
        201
      )
    );
    const user = userEvent.setup();
    renderConfirm();
    await user.click(screen.getByRole("button", { name: "Bevestig" }));
    expect(await screen.findByRole("status")).toHaveTextContent("€ 40,00");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("a pre-fill opens the normal screen, and only for internal paths", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
      Promise.resolve(
        String(input).endsWith("/from-moment")
          ? json(proposal({}), 201)
          : json(
              proposal({
                status: "executed",
                outcome: {
                  kind: "navigate",
                  message: "Controleer en bevestig je overschrijving.",
                  navigate_to: "/transfer?to_name=Lucas&amount=25.00",
                  handoff_summary: null,
                },
              })
            )
      )
    );
    const user = userEvent.setup();
    renderConfirm();
    await user.click(screen.getByRole("button", { name: "Bevestig" }));
    expect(await screen.findByRole("link", { name: "Verder" })).toHaveAttribute(
      "href",
      "/transfer?to_name=Lucas&amount=25.00"
    );
  });

  it("shows the server's reason when it refuses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ detail: "Er staat niet genoeg op je zichtrekening." }, 409)
    );
    const user = userEvent.setup();
    renderConfirm();
    await user.click(screen.getByRole("button", { name: "Bevestig" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Er staat niet genoeg op je zichtrekening.");
    expect(screen.getByRole("button", { name: "Bevestig" })).toBeEnabled();
  });

  it("'Nee, bedankt' dismisses the moment", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const user = userEvent.setup();
    const { onDismissed } = renderConfirm();
    await user.click(screen.getByRole("button", { name: "Nee, bedankt" }));
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/v1/kate/feed/first_salary/dismiss");
    expect(onDismissed).toHaveBeenCalled();
  });

  it("level 'suggest': explains, no confirm button, points to the consent screen", () => {
    renderConfirm({ action: { ...action, level: "suggest", can_confirm: false } });
    expect(screen.getByText(action.summary)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Bevestig" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Wat weet en mag Kate/ })).toHaveAttribute("href", "/kate");
  });
});
