"use client";

import { ColorType, createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { usePriceHistory } from "@/hooks/usePriceHistory";
import { usePrices } from "@/context/PriceContext";
import { formatCurrency, formatPercent, pnlColorClass } from "@/lib/format";

export default function MainChart({ ticker }: { ticker: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const points = usePriceHistory(ticker);
  const { prices } = usePrices();
  const live = ticker ? prices[ticker] : undefined;

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9ca3af",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1f2330" },
        horzLines: { color: "#1f2330" },
      },
      rightPriceScale: { borderColor: "#2a2e3a" },
      timeScale: { borderColor: "#2a2e3a", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 0 },
    });

    const series = chart.addAreaSeries({
      lineColor: "#209dd7",
      topColor: "rgba(32, 157, 215, 0.28)",
      bottomColor: "rgba(32, 157, 215, 0.02)",
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || points.length === 0) return;
    seriesRef.current.setData(points);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  const changePct =
    live && live.previousPrice ? ((live.price - live.previousPrice) / live.previousPrice) * 100 : 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-baseline justify-between px-4 pt-3">
        <div>
          <span className="font-mono text-xl font-semibold text-gray-100">{ticker ?? "—"}</span>
          {live && (
            <span className="ml-3 font-mono text-lg text-gray-300">{formatCurrency(live.price)}</span>
          )}
          {live && (
            <span className={`ml-2 font-mono text-sm ${pnlColorClass(changePct)}`}>
              {formatPercent(changePct)}
            </span>
          )}
        </div>
        <span className="text-[11px] uppercase tracking-wide text-gray-500">Last 30 min</span>
      </div>
      <div ref={containerRef} className="min-h-0 flex-1 px-2 pb-2" />
    </div>
  );
}
