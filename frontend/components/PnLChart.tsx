"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { usePortfolio } from "@/context/PortfolioContext";
import { formatCurrency } from "@/lib/format";

interface ChartRow {
  time: string;
  value: number;
}

const REFRESH_MS = 30000;

export default function PnLChart() {
  const [rows, setRows] = useState<ChartRow[]>([]);
  const { portfolio } = usePortfolio();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await api.getPortfolioHistory();
        if (cancelled) return;
        setRows(
          res.snapshots.map((s) => ({
            time: new Date(s.recorded_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            value: s.total_value,
          }))
        );
      } catch {
        // best-effort; keep prior data on transient failure
      }
    }

    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const liveRows =
    portfolio && rows.length > 0
      ? [...rows.slice(0, -1), { ...rows[rows.length - 1], value: portfolio.total_value }]
      : rows;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">P&amp;L</h2>
      </div>
      <div className="min-h-0 flex-1 p-2">
        {liveRows.length < 2 ? (
          <p className="p-2 text-sm text-gray-500">Building history…</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={liveRows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2330" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#6b7280" }} minTickGap={30} />
              <YAxis
                tick={{ fontSize: 10, fill: "#6b7280" }}
                width={64}
                domain={["auto", "auto"]}
                tickFormatter={(v) => formatCurrency(v)}
              />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2e3a", fontSize: 12 }}
                labelStyle={{ color: "#9ca3af" }}
                formatter={(value: number) => [formatCurrency(value), "Total value"]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#209dd7"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
