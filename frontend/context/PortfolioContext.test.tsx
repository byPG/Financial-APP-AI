import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PositionsTable from "@/components/PositionsTable";
import { PortfolioProvider } from "./PortfolioContext";
import type { Portfolio } from "@/types/api";

vi.mock("@/lib/api", () => ({
  api: {
    getPortfolio: vi.fn(
      async (): Promise<Portfolio> => ({
        cash_balance: 5000,
        positions: [
          {
            ticker: "AAPL",
            quantity: 10,
            avg_cost: 150,
            current_price: 190,
            market_value: 1900,
            unrealized_pnl: 400,
            unrealized_pnl_pct: 26.67,
          },
        ],
        total_value: 6900,
        total_unrealized_pnl: 400,
      })
    ),
  },
  ApiError: class ApiError extends Error {},
}));

describe("PortfolioContext + PositionsTable", () => {
  it("loads the portfolio and renders position P&L", async () => {
    render(
      <PortfolioProvider>
        <PositionsTable />
      </PortfolioProvider>
    );

    await waitFor(() => expect(screen.getByText("AAPL")).toBeInTheDocument());
    expect(screen.getByText("$150.00")).toBeInTheDocument();
    expect(screen.getByText("$190.00")).toBeInTheDocument();
    expect(screen.getByText("+$400.00")).toBeInTheDocument();
    expect(screen.getByText("+26.67%")).toBeInTheDocument();
  });

  it("shows an empty state with no positions", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getPortfolio).mockResolvedValueOnce({
      cash_balance: 10000,
      positions: [],
      total_value: 10000,
      total_unrealized_pnl: 0,
    });

    render(
      <PortfolioProvider>
        <PositionsTable />
      </PortfolioProvider>
    );

    await waitFor(() => expect(screen.getByText(/no open positions/i)).toBeInTheDocument());
  });
});
