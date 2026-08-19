"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { usePrices } from "@/context/PriceContext";
import type { UTCTimestamp } from "lightweight-charts";

export interface ChartPoint {
  time: UTCTimestamp;
  value: number;
}

const REFETCH_INTERVAL_MS = 15000;

function toUnixSeconds(iso: string): number {
  return Math.floor(new Date(iso).getTime() / 1000);
}

/**
 * Polls GET /api/prices/{ticker}/history (backend appends a downsampled
 * point every ~10-15s, planning/PLAN.md Section 6) and tops it off with the
 * latest SSE tick so sparklines/main chart feel live between polls.
 */
export function usePriceHistory(ticker: string | null): ChartPoint[] {
  const [history, setHistory] = useState<ChartPoint[]>([]);
  const { prices } = usePrices();
  const lastTimeRef = useRef(0);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;

    async function load() {
      try {
        const res = await api.getPriceHistory(ticker!);
        if (cancelled) return;
        const points = res.points
          .map((p) => ({ time: toUnixSeconds(p.timestamp) as UTCTimestamp, value: p.price }))
          .sort((a, b) => a.time - b.time);
        if (points.length > 0) {
          lastTimeRef.current = points[points.length - 1].time;
        }
        setHistory(points);
      } catch {
        // history endpoint 404s only for untracked tickers; leave state as-is
      }
    }

    load();
    const interval = setInterval(load, REFETCH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [ticker]);

  const live = ticker ? prices[ticker] : undefined;

  useEffect(() => {
    if (!ticker || !live) return;
    const time = Math.max(Math.floor(Date.now() / 1000), lastTimeRef.current + 1) as UTCTimestamp;
    lastTimeRef.current = time;
    setHistory((prev) => [...prev, { time, value: live.price }].slice(-400));
    // Only re-run when a new tick arrives for this ticker.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live?.tick, ticker]);

  return history;
}
