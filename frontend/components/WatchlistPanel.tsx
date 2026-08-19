"use client";

import { useState } from "react";
import PriceCell from "@/components/PriceCell";
import Sparkline from "@/components/Sparkline";
import { usePrices } from "@/context/PriceContext";
import { useWatchlist } from "@/context/WatchlistContext";
import { ApiError } from "@/lib/api";
import { formatPercent, pnlColorClass } from "@/lib/format";

export default function WatchlistPanel({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (ticker: string) => void;
}) {
  const { items, addTicker, removeTicker } = useWatchlist();
  const { prices } = usePrices();
  const [newTicker, setNewTicker] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newTicker.trim()) return;
    setPending(true);
    setFormError(null);
    try {
      await addTicker(newTicker);
      setNewTicker("");
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to add ticker");
    } finally {
      setPending(false);
    }
  }

  async function handleRemove(ticker: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await removeTicker(ticker);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : `Failed to remove ${ticker}`);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Watchlist</h2>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-bg-panel text-[11px] uppercase text-gray-500">
            <tr>
              <th className="px-3 py-1.5 text-left font-medium">Ticker</th>
              <th className="px-3 py-1.5 text-right font-medium">Price</th>
              <th className="px-3 py-1.5 text-right font-medium">Chg</th>
              <th className="px-2 py-1.5 text-right font-medium">30m</th>
              <th className="w-6 px-2 py-1.5" />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const live = prices[item.ticker];
              const changePct =
                live && live.previousPrice
                  ? ((live.price - live.previousPrice) / live.previousPrice) * 100
                  : 0;
              const isSelected = selected === item.ticker;
              return (
                <tr
                  key={item.ticker}
                  onClick={() => onSelect(item.ticker)}
                  className={`cursor-pointer border-b border-border-muted/60 hover:bg-bg-raised ${
                    isSelected ? "bg-bg-raised" : ""
                  }`}
                >
                  <td className="px-3 py-1.5 font-mono font-medium text-gray-100">
                    {item.ticker}
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <PriceCell live={live} />
                  </td>
                  <td className={`px-3 py-1.5 text-right font-mono text-xs ${pnlColorClass(changePct)}`}>
                    {live ? formatPercent(changePct) : "—"}
                  </td>
                  <td className="px-2 py-1.5">
                    <Sparkline ticker={item.ticker} />
                  </td>
                  <td className="px-2 py-1.5 text-right">
                    <button
                      onClick={(e) => handleRemove(item.ticker, e)}
                      title={`Remove ${item.ticker}`}
                      className="text-gray-600 hover:text-down"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleAdd} className="border-t border-border-muted p-2">
        <div className="flex gap-2">
          <input
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            placeholder="Add ticker"
            maxLength={5}
            className="min-w-0 flex-1 rounded border border-border-muted bg-bg-base px-2 py-1 font-mono text-sm uppercase text-gray-100 outline-none focus:border-blue-primary"
          />
          <button
            type="submit"
            disabled={pending}
            className="rounded bg-purple-secondary px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
          >
            Add
          </button>
        </div>
        {formError && <p className="mt-1 text-xs text-down">{formError}</p>}
      </form>
    </div>
  );
}
