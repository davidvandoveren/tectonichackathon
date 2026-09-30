import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChannelNotification } from "./ChannelNotification";
import { DemoPage } from "./DemoPage";
import { bandOf, type FeedItem } from "./momentsApi";
import { SilencedList } from "./SilencedList";
import { UrgencyMeter } from "./UrgencyMeter";

function item(overrides: Partial<FeedItem>): FeedItem {
  return {
    id: "first_salary",
    title: "Proficiat met je eerste loon!",
    body: "…",
    urgency: 39,
    channel: "feed",
    reason: "…",
    cta_label: "Start met sparen",
    cta_target: "/transfer",
    requires_advisor: false,
    ...overrides,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("UrgencyMeter", () => {
  it("uses the non-overlapping bands from the API contract", () => {
    expect(bandOf(98)).toBe("risk");
    expect(bandOf(70)).toBe("risk");
    expect(bandOf(57)).toBe("obligation");
    expect(bandOf(39)).toBe("opportunity");
  });

  it("shows urgency and an interruptive channel", () => {
    render(<UrgencyMeter urgency={98} channel="sms" />);

    expect(screen.getByRole("meter", { name: "Urgentie" })).toHaveAttribute("aria-valuenow", "98");
    expect(screen.getByText("Dringend · 98")).toBeInTheDocument();
    expect(screen.getByText("Sms")).toBeInTheDocument();
  });

  it("does not label the quiet in-app channel", () => {
    render(<UrgencyMeter urgency={39} channel="feed" />);

    expect(screen.getByText("Kans · 39")).toBeInTheDocument();
    expect(screen.queryByText(/feed/i)).not.toBeInTheDocument();
  });

  it("renders nothing for an older backend without urgency", () => {
    const { container } = render(<UrgencyMeter />);

    expect(container).toBeEmptyDOMElement();
  });
});

describe("ChannelNotification", () => {
  it("shows only the item Kate chose to interrupt with", () => {
    render(
      <ChannelNotification
        items={[
          item({ id: "income_missing", title: "Je loon is nog niet gestort", urgency: 98, channel: "sms" }),
          item({}),
        ]}
      />
    );

    expect(screen.getByRole("status")).toHaveTextContent("Je loon is nog niet gestort");
    expect(screen.getByText("Sms · nu")).toBeInTheDocument();
    expect(screen.queryByText("Proficiat met je eerste loon!")).not.toBeInTheDocument();
  });

  it("stays away when everything waits quietly in the feed", () => {
    const { container } = render(<ChannelNotification items={[item({})]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("can be closed", async () => {
    render(<ChannelNotification items={[item({ channel: "push" })]} />);

    await userEvent.click(screen.getByRole("button", { name: "Melding sluiten" }));

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("SilencedList", () => {
  it("explains what Kate deliberately kept quiet about", async () => {
    render(
      <SilencedList
        silenced={[{ moment: "deal_match", reason_code: "cashflow_first", reason: "Je saldo staat krap." }]}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /Bewust niet gezegd/ }));

    expect(screen.getByText("Je saldo staat krap.")).toBeInTheDocument();
  });

  it("renders nothing when Kate held nothing back", () => {
    const { container } = render(<SilencedList silenced={[]} />);

    expect(container).toBeEmptyDOMElement();
  });
});

describe("DemoPage", () => {
  function renderDemo() {
    render(
      <MemoryRouter initialEntries={["/demo"]}>
        <Routes>
          <Route path="/demo" element={<DemoPage />} />
          <Route path="/" element={<p>home</p>} />
        </Routes>
      </MemoryRouter>
    );
  }

  it("moves the clock and goes home to show what Kate does", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ days_shifted: 40, clock_offset_days: 40, today: "2026-11-09", username: "jan", injected: 0, feed: { items: [], silenced: [] } })
    );
    renderDemo();

    await userEvent.click(screen.getByRole("button", { name: "+40 dagen · loon blijft uit" }));

    expect(await screen.findByText("home")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/admin/time-machine");
    expect(JSON.parse(String(init?.body))).toEqual({ days: 40, scenario: "salary_missing" });
  });

  it("tells a non-admin that the time machine is not for them", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: "Not Found" }, 404));
    renderDemo();

    await userEvent.click(screen.getByRole("button", { name: "+7 dagen" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("demo-admin");
  });
});
