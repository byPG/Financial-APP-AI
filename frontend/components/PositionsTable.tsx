"use client";

import { usePortfolio } from "@/context/PortfolioContext";
import { formatCurrency, formatPercent, formatQuantity, formatSignedCurrency, pnlColorClass } from "@/lib/format";

export default function PositionsTable() {
  const { portfolio } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Positions</h2>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {positions.length === 0 ? (
          <p className="px-3 py-4 text-sm text-gray-500">No open positions.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-bg-panel text-[11px] uppercase text-gray-500">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">Ticker</th>
                <th className="px-3 py-1.5 text-right font-medium">Qty</th>
                <th className="px-3 py-1.5 text-right font-medium">Avg Cost</th>
                <th className="px-3 py-1.5 text-right font-medium">Price</th>
                <th className="px-3 py-1.5 text-right font-medium">P&L</th>
                <th className="px-3 py-1.5 text-right font-medium">%</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.ticker} className="border-b border-border-muted/60">
                  <td className="px-3 py-1.5 font-mono font-medium text-gray-100">{p.ticker}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-gray-300">
                    {formatQuantity(p.quantity)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-gray-300">
                    {formatCurrency(p.avg_cost)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-gray-300">
                    {formatCurrency(p.current_price)}
                  </td>
                  <td className={`px-3 py-1.5 text-right font-mono ${pnlColorClass(p.unrealized_pnl)}`}>
                    {formatSignedCurrency(p.unrealized_pnl)}
                  </td>
                  <td className={`px-3 py-1.5 text-right font-mono ${pnlColorClass(p.unrealized_pnl_pct)}`}>
                    {formatPercent(p.unrealized_pnl_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
