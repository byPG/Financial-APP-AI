"use client";

import ConnectionDot from "@/components/ConnectionDot";
import { usePortfolio } from "@/context/PortfolioContext";
import { usePrices } from "@/context/PriceContext";
import { formatCurrency, formatSignedCurrency, pnlColorClass } from "@/lib/format";

export default function Header() {
  const { portfolio } = usePortfolio();
  const { status } = usePrices();

  return (
    <header className="flex items-center justify-between border-b border-border-muted bg-bg-panel px-6 py-3">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-tight text-accent-yellow">FinAlly</span>
        <span className="hidden text-xs text-gray-500 sm:inline">AI Trading Workstation</span>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Portfolio Value</div>
          <div className="font-mono text-lg font-semibold text-gray-100">
            {portfolio ? formatCurrency(portfolio.total_value) : "—"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Cash</div>
          <div className="font-mono text-lg text-blue-primary">
            {portfolio ? formatCurrency(portfolio.cash_balance) : "—"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Unrealized P&L</div>
          <div
            className={`font-mono text-lg font-semibold ${
              portfolio ? pnlColorClass(portfolio.total_unrealized_pnl) : "text-gray-400"
            }`}
          >
            {portfolio ? formatSignedCurrency(portfolio.total_unrealized_pnl) : "—"}
          </div>
        </div>
        <ConnectionDot status={status} />
      </div>
    </header>
  );
}
