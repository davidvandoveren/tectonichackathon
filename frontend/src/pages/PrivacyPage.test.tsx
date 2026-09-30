import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { PrivacyPage } from "./PrivacyPage";

describe("PrivacyPage", () => {
  it("states the disclaimer, the AI disclosure and how to report a vulnerability", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { level: 1, name: "Privacy & AI" })).toBeInTheDocument();
    expect(screen.getByText(/geen officieel product of dienst van KBC/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kate is een AI" })).toBeInTheDocument();
    const report = screen.getByRole("link", { name: "GitHub Security Advisories" });
    expect(report).toHaveAttribute("rel", "noopener noreferrer");
  });
});
