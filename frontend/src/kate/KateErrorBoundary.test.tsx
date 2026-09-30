import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KateErrorBoundary } from "./KateErrorBoundary";

let shouldThrow = true;

function Exploding() {
  if (shouldThrow) throw new Error("boom");
  return <p>Kate werkt</p>;
}

function App() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <button type="button" onClick={() => setCount((c) => c + 1)}>
        Rest van de app {count}
      </button>
      <KateErrorBoundary>
        <Exploding />
      </KateErrorBoundary>
    </div>
  );
}

afterEach(() => vi.restoreAllMocks());

describe("KateErrorBoundary", () => {
  it("keeps the rest of the app alive and lets Kate restart", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("alert")).toHaveTextContent("Er ging iets mis met Kate");
    await user.click(screen.getByRole("button", { name: /Rest van de app/ }));
    expect(screen.getByRole("button", { name: "Rest van de app 1" })).toBeInTheDocument();

    shouldThrow = false;
    await user.click(screen.getByRole("button", { name: "Kate herstarten" }));
    expect(screen.getByText("Kate werkt")).toBeInTheDocument();
  });
});
