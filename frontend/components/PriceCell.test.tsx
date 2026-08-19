import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PriceCell from "./PriceCell";
import type { LivePrice } from "@/context/PriceContext";

function makeLive(overrides: Partial<LivePrice>): LivePrice {
  return {
    ticker: "AAPL",
    price: 190.5,
    previousPrice: 189.0,
    timestamp: "2026-08-19T10:00:00Z",
    direction: "up",
    tick: 1,
    ...overrides,
  };
}

describe("PriceCell", () => {
  it("renders a dash when there is no live price yet", () => {
    render(<PriceCell live={undefined} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders the formatted price", () => {
    render(<PriceCell live={makeLive({})} />);
    expect(screen.getByText("$190.50")).toBeInTheDocument();
  });

  it("applies the flash-up class on an uptick", () => {
    render(<PriceCell live={makeLive({ direction: "up" })} />);
    expect(screen.getByText("$190.50")).toHaveClass("flash-up");
  });

  it("applies the flash-down class on a downtick", () => {
    render(<PriceCell live={makeLive({ direction: "down", price: 188.0 })} />);
    expect(screen.getByText("$188.00")).toHaveClass("flash-down");
  });

  it("applies no flash class when flat", () => {
    render(<PriceCell live={makeLive({ direction: "flat" })} />);
    const el = screen.getByText("$190.50");
    expect(el).not.toHaveClass("flash-up");
    expect(el).not.toHaveClass("flash-down");
  });
});
