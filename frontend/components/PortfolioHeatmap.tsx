"use client";

import { Treemap, ResponsiveContainer } from "recharts";
import { usePortfolio } from "@/context/PortfolioContext";
import { formatPercent } from "@/lib/format";

interface HeatmapNode {
  name: string;
  size: number;
  pnlPct: number;
}

function colorForPnl(pnlPct: number): string {
  // Green for profit, red for loss, intensity scales with magnitude.
  const magnitude = Math.min(Math.abs(pnlPct) / 15, 1); // saturate around +-15%
  if (pnlPct >= 0) {
    const lightness = 45 - magnitude * 15; // darker green as gains grow
    return `hsl(142, 60%, ${lightness}%)`;
  }
  const lightness = 45 - magnitude * 15;
  return `hsl(0, 65%, ${lightness}%)`;
}

function CellContent(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPct?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, pnlPct = 0 } = props;
  if (width < 2 || height < 2) return null;
  const showText = width > 40 && height > 28;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={colorForPnl(pnlPct)}
        stroke="#0d1117"
        strokeWidth={2}
      />
      {showText && (
        <>
          <text x={x + 6} y={y + 16} fontSize={12} fontFamily="var(--font-mono)" fill="#f3f4f6">
            {name}
          </text>
          <text x={x + 6} y={y + 30} fontSize={10} fontFamily="var(--font-mono)" fill="#e5e7eb99">
            {formatPercent(pnlPct)}
          </text>
        </>
      )}
    </g>
  );
}

export default function PortfolioHeatmap() {
  const { portfolio } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  const data: HeatmapNode[] = positions
    .filter((p) => p.market_value > 0)
    .map((p) => ({ name: p.ticker, size: p.market_value, pnlPct: p.unrealized_pnl_pct }));

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
          Portfolio Heatmap
        </h2>
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length === 0 ? (
          <p className="p-2 text-sm text-gray-500">No open positions to visualize.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              stroke="#0d1117"
              isAnimationActive={false}
              content={<CellContent />}
            />
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
