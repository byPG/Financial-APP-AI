"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import Header from "@/components/Header";
import MainChart from "@/components/MainChart";
import PnLChart from "@/components/PnLChart";
import PortfolioHeatmap from "@/components/PortfolioHeatmap";
import PositionsTable from "@/components/PositionsTable";
import TradeBar from "@/components/TradeBar";
import WatchlistPanel from "@/components/WatchlistPanel";
import { PortfolioProvider } from "@/context/PortfolioContext";
import { PriceProvider } from "@/context/PriceContext";
import { useWatchlist, WatchlistProvider } from "@/context/WatchlistContext";

function Dashboard() {
  const { items } = useWatchlist();
  const [selected, setSelected] = useState<string | null>(null);

  // Defaults to the first watchlist ticker on initial load (PLAN.md Section 10).
  useEffect(() => {
    if (!selected && items.length > 0) {
      setSelected(items[0].ticker);
    }
  }, [items, selected]);

  return (
    <div className="flex h-screen flex-col bg-bg-base">
      <Header />

      <div className="grid min-h-0 flex-1 grid-cols-12 grid-rows-6 gap-2 p-2">
        <section className="col-span-3 row-span-6 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <WatchlistPanel selected={selected} onSelect={setSelected} />
        </section>

        <section className="col-span-6 row-span-4 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <MainChart ticker={selected} />
        </section>

        <section className="col-span-3 row-span-6 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <ChatPanel />
        </section>

        <section className="col-span-3 row-span-2 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <PortfolioHeatmap />
        </section>

        <section className="col-span-3 row-span-2 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <PnLChart />
        </section>
      </div>

      <div className="grid grid-cols-12 gap-2 px-2 pb-2">
        <section className="col-span-9 overflow-hidden rounded border border-border-muted bg-bg-panel">
          <div className="max-h-40 overflow-y-auto">
            <PositionsTable />
          </div>
        </section>
      </div>

      <TradeBar selectedTicker={selected} onTicker={setSelected} />
    </div>
  );
}

export default function Home() {
  return (
    <PriceProvider>
      <WatchlistProvider>
        <PortfolioProvider>
          <Dashboard />
        </PortfolioProvider>
      </WatchlistProvider>
    </PriceProvider>
  );
}
