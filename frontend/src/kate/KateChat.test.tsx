import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KateChat } from "./KateChat";
import { transferLink } from "./kateApi";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.restoreAllMocks());

describe("KateChat", () => {
  it("shows a transfer proposal the customer still has to confirm", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/kate/status")) {
        return Promise.resolve(jsonResponse({ llm: "mock", voice: false, speech_recognition: false }));
      }
      return Promise.resolve(
        jsonResponse({
          reply: "Ik ben Kate (AI). Overschrijving klaargezet.",
          mode: "normal",
          action: { type: "transfer", to_name: "Lucas", amount: "25.00", description: "Pizza", summary: null },
        })
      );
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <KateChat />
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "Open Kate" }));
    expect(screen.getByText(/Ik ben een AI/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Bericht aan Kate"), "Stuur Lucas 25 euro voor de pizza");
    await user.click(screen.getByRole("button", { name: "Stuur" }));

    const link = await screen.findByRole("link", { name: "Controleer en bevestig" });
    expect(link).toHaveAttribute("href", "/transfer?to_name=Lucas&amount=25.00&description=Pizza");
    expect(screen.getByText(/Je bevestigt op het gewone overschrijvingsscherm/)).toBeInTheDocument();
  });

  it("builds an encoded internal transfer link", () => {
    const href = transferLink({
      type: "transfer",
      to_name: "A&B //evil",
      amount: "1.00",
      description: null,
      summary: null,
    });
    expect(href.startsWith("/transfer?")).toBe(true);
    expect(href).toContain("to_name=A%26B+%2F%2Fevil");
  });

  it("confirms a chat proposal through Kate Skills and opens the prefilled transfer", async () => {
    const calls: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      calls.push(url);
      if (url.endsWith("/kate/status")) {
        return Promise.resolve(jsonResponse({ llm: "gemini", voice: false, speech_recognition: false }));
      }
      if (url.endsWith("/approve")) {
        return Promise.resolve(
          jsonResponse({
            id: "p_1",
            status: "executed",
            outcome: { kind: "navigate", message: "ok", navigate_to: "/transfer?to_name=Lucas&amount=25.00", handoff_summary: null },
          })
        );
      }
      return Promise.resolve(
        jsonResponse({
          reply: "Klaargezet (AI).",
          mode: "normal",
          action: { type: "transfer", to_name: "Lucas", amount: "25.00", description: "Pizza", summary: null, proposal_id: "p_1", proposal_status: "pending" },
        })
      );
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<KateChat />} />
          <Route path="/transfer" element={<p>Overschrijvingsscherm</p>} />
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "Open Kate" }));
    await user.type(screen.getByLabelText("Bericht aan Kate"), "Stuur Lucas 25 euro");
    await user.click(screen.getByRole("button", { name: "Stuur" }));
    await user.click(await screen.findByRole("button", { name: "Bevestigen" }));

    expect(await screen.findByText("Overschrijvingsscherm")).toBeInTheDocument();
    expect(calls.some((url) => url.endsWith("/proposals/p_1/approve"))).toBe(true);
  });
});
