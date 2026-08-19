import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatActionBadges from "./ChatActionBadges";

describe("ChatActionBadges", () => {
  it("renders nothing when there are no actions", () => {
    const { container } = render(<ChatActionBadges actions={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders an executed trade badge", () => {
    render(
      <ChatActionBadges
        actions={{
          trades: [{ ticker: "AAPL", side: "buy", quantity: 10, status: "executed", error: null }],
          watchlist_changes: [],
        }}
      />
    );
    expect(screen.getByText(/buy 10 AAPL/)).toBeInTheDocument();
  });

  it("renders a failed watchlist change badge", () => {
    render(
      <ChatActionBadges
        actions={{
          trades: [],
          watchlist_changes: [
            { ticker: "PYPL", action: "add", status: "failed", error: "already exists" },
          ],
        }}
      />
    );
    const badge = screen.getByText(/add PYPL/);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("title", "already exists");
  });
});
