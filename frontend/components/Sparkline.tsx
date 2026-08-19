"use client";

import { ColorType, createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { usePriceHistory } from "@/hooks/usePriceHistory";

export default function Sparkline({
  ticker,
  width = 120,
  height = 36,
}: {
  ticker: string;
  width?: number;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const points = usePriceHistory(ticker);

  useEffect(() => {
    if (!containerRef.current) return;

    const isUp = points.length >= 2 ? points[points.length - 1].value >= points[0].value : true;
    const lineColor = isUp ? "#22c55e" : "#ef4444";

    const chart = createChart(containerRef.current, {
      width,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "transparent",
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
      handleScroll: false,
      handleScale: false,
    });

    const series = chart.addAreaSeries({
      lineColor,
      topColor: `${lineColor}33`,
      bottomColor: `${lineColor}00`,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
    // Chart is fully recreated when direction color would change; cheap at this size.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [width, height]);

  useEffect(() => {
    if (!seriesRef.current || points.length === 0) return;
    seriesRef.current.setData(points);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  if (points.length < 2) {
    return <div style={{ width, height }} className="flex items-center justify-center text-[10px] text-gray-600">…</div>;
  }

  return <div ref={containerRef} style={{ width, height }} />;
}
