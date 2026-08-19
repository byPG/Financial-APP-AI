"use client";

import { useState } from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import { usePrices } from "@/context/PriceContext";
import { useWatchlist } from "@/context/WatchlistContext";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function TradeBar({
  selectedTicker,
  onTicker,
}: {
  selectedTicker: string | null;
  onTicker: (ticker: string) => void;
}) {
  const { items } = useWatchlist();
  const { prices } = usePrices();
  const { trade } = usePortfolio();
  const [quantity, setQuantity] = useState("1");
  const [pending, setPending] = useState<"buy" | "sell" | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const ticker = selectedTicker ?? items[0]?.ticker ?? null;
  const live = ticker ? prices[ticker] : undefined;
  const qtyNum = Number(quantity);

  async function submit(side: "buy" | "sell") {
    if (!ticker || !qtyNum || qtyNum <= 0) return;
    setPending(side);
    setMessage(null);
    try {
      await trade(ticker, qtyNum, side);
      setMessage({ kind: "ok", text: `${side === "buy" ? "Bought" : "Sold"} ${qtyNum} ${ticker}` });
    } catch (err) {
      setMessage({ kind: "err", text: err instanceof ApiError ? err.message : "Trade failed" });
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="flex items-center gap-3 border-t border-border-muted bg-bg-panel px-4 py-3">
      <select
        value={ticker ?? ""}
        onChange={(e) => onTicker(e.target.value)}
        className="rounded border border-border-muted bg-bg-base px-2 py-1.5 font-mono text-sm text-gray-100 outline-none focus:border-blue-primary"
      >
        {items.map((item) => (
          <option key={item.ticker} value={item.ticker}>
            {item.ticker}
          </option>
        ))}
      </select>

      <input
        type="number"
        min="0"
        step="any"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="w-24 rounded border border-border-muted bg-bg-base px-2 py-1.5 font-mono text-sm text-gray-100 outline-none focus:border-blue-primary"
      />

      <span className="font-mono text-sm text-gray-400">
        {live ? `@ ${formatCurrency(live.price)}` : ""}
      </span>

      <button
        onClick={() => submit("buy")}
        disabled={!ticker || pending !== null}
        className="rounded bg-up px-4 py-1.5 text-sm font-semibold text-black disabled:opacity-50"
      >
        Buy
      </button>
      <button
        onClick={() => submit("sell")}
        disabled={!ticker || pending !== null}
        className="rounded bg-down px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
      >
        Sell
      </button>

      {message && (
        <span className={`text-xs ${message.kind === "ok" ? "text-up" : "text-down"}`}>
          {message.text}
        </span>
      )}
    </div>
  );
}
