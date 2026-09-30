import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { InsightCard } from "./InsightCard";
import type { Insight } from "../api/types";

const insight: Insight = {
  id: "i_1",
  kind: "moment",
  title: "Eerste loon ontvangen?",
  body: "We zagen een nieuwe inkomstenbron.",
  cta_label: "Start met sparen",
  cta_target: "/transfer",
  reason: "We zagen een nieuwe maandelijkse storting van je werkgever.",
};

describe("InsightCard", () => {
  it("shows the title, body and CTA", () => {
    render(
      <MemoryRouter>
        <InsightCard insight={insight} />
      </MemoryRouter>
    );
    expect(screen.getByText(insight.title)).toBeInTheDocument();
    expect(screen.getByText(insight.body)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: insight.cta_label })).toBeInTheDocument();
  });

  it("hides the reason until 'Waarom zie ik dit?' is activated", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <InsightCard insight={insight} />
      </MemoryRouter>
    );

    expect(screen.queryByText(insight.reason)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /waarom zie ik dit/i }));

    expect(screen.getByText(insight.reason)).toBeInTheDocument();
  });

  it("ignores an unsafe cta_target", () => {
    render(
      <MemoryRouter>
        <InsightCard insight={{ ...insight, cta_target: "//evil.example.com" }} />
      </MemoryRouter>
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
