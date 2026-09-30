import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KateChat } from "./KateChat";
import { MAX_HISTORY, MAX_MESSAGE, MAX_TURN_TEXT, sendKateMessage, transferLink } from "./kateApi";

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

  it("sends a too-long question once, shortened, and says so instead of failing", async () => {
    const chatBodies: { message: string; history: unknown[] }[] = [];
    let answer: (response: Response) => void = () => undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/kate/status")) {
        return Promise.resolve(jsonResponse({ llm: "gemini", voice: false, speech_recognition: false }));
      }
      if (url.endsWith("/kate/voice")) {
        return Promise.resolve(jsonResponse({ voice: "female", default_voice: "female", available: [] }));
      }
      chatBodies.push(JSON.parse(String(init?.body)) as { message: string; history: unknown[] });
      return new Promise<Response>((resolve) => {
        answer = resolve;
      });
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <KateChat />
      </MemoryRouter>
    );
    await user.click(screen.getByRole("button", { name: "Open Kate" }));

    const input = screen.getByLabelText("Bericht aan Kate");
    await user.click(input);
    await user.paste("a".repeat(3000));
    // Nothing is silently cut off while typing or pasting: the counter warns first.
    expect(input).toHaveValue("a".repeat(3000));
    expect(screen.getByText(/3000\/1000/)).toBeInTheDocument();

    // A rapid double submit (double tap, Enter + click) must send one request only.
    const form = input.closest("form");
    if (!form) throw new Error("no form");
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(chatBodies).toHaveLength(1));
    expect(chatBodies[0]?.message).toHaveLength(1000);

    answer(
      jsonResponse({
        reply: "Ik ben Kate (AI). Hier is mijn antwoord.",
        mode: "normal",
        action: { type: "none", to_name: null, amount: null, description: null, summary: null },
        truncated: false,
      })
    );
    expect(await screen.findByText(/Hier is mijn antwoord/)).toBeInTheDocument();
    expect(screen.getByText(/eerste 1000 tekens/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a friendly error and keeps the chat usable when Kate refuses the request", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/kate/status")) {
        return Promise.resolve(jsonResponse({ llm: "gemini", voice: false, speech_recognition: false }));
      }
      if (url.endsWith("/kate/voice")) {
        return Promise.resolve(jsonResponse({ voice: "female", default_voice: "female", available: [] }));
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Even rustig aan, probeer zo weer" }), {
          status: 429,
          headers: { "Content-Type": "application/json" },
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
    await user.type(screen.getByLabelText("Bericht aan Kate"), "hoi");
    await user.click(screen.getByRole("button", { name: "Stuur" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Even rustig aan");
    expect(screen.getByLabelText("Bericht aan Kate")).toBeEnabled();
  });

  it("never sends more than the API accepts", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ reply: "ok", mode: "normal", action: { type: "none" }, truncated: true })
    );
    const history = Array.from({ length: 40 }, (_, i) => ({
      role: i % 2 ? ("kate" as const) : ("user" as const),
      text: "b".repeat(5000),
    }));
    await sendKateMessage("c".repeat(9000), history);
    const body = JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body)) as {
      message: string;
      history: { text: string }[];
    };
    expect(body.message).toHaveLength(MAX_MESSAGE);
    expect(body.history).toHaveLength(MAX_HISTORY);
    expect(body.history.every((turn) => turn.text.length <= MAX_TURN_TEXT)).toBe(true);
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
