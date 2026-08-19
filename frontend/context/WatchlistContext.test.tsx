import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import WatchlistPanel from "@/components/WatchlistPanel";
import { PriceProvider } from "./PriceContext";
import { WatchlistProvider } from "./WatchlistContext";
import type { WatchlistItem, WatchlistResponse } from "@/types/api";

const items: WatchlistItem[] = [
  { ticker: "AAPL", added_at: "2026-08-19T00:00:00Z", current_price: 190, previous_price: 189 },
];

vi.mock("@/lib/api", () => ({
  api: {
    getWatchlist: vi.fn(async (): Promise<WatchlistResponse> => ({ items })),
    addTicker: vi.fn(async () => ({})),
    removeTicker: vi.fn(async () => {}),
    getPriceHistory: vi.fn(async () => ({ ticker: "AAPL", points: [] })),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  sseUrl: (path: string) => path,
}));

function renderPanel() {
  return render(
    <PriceProvider>
      <WatchlistProvider>
        <WatchlistPanel selected={null} onSelect={() => {}} />
      </WatchlistProvider>
    </PriceProvider>
  );
}

describe("WatchlistContext + WatchlistPanel", () => {
  it("loads and renders the watchlist", async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByText("AAPL")).toBeInTheDocument());
  });

  it("rejects an invalid ticker before calling the API", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");
    renderPanel();
    await waitFor(() => expect(screen.getByText("AAPL")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText("Add ticker"), "12345");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText(/1-5 uppercase letters/)).toBeInTheDocument();
    expect(api.addTicker).not.toHaveBeenCalled();
  });

  it("removes a ticker and refreshes the list", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");
    renderPanel();
    await waitFor(() => expect(screen.getByText("AAPL")).toBeInTheDocument());

    await user.click(screen.getByTitle("Remove AAPL"));

    await waitFor(() => expect(api.removeTicker).toHaveBeenCalledWith("AAPL"));
  });
});
