"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { sseUrl } from "@/lib/api";
import type { ChangeDirection, PriceUpdateEvent } from "@/types/api";

export type ConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface LivePrice {
  ticker: string;
  price: number;
  previousPrice: number;
  timestamp: string;
  direction: ChangeDirection;
  /** bumped on every update so consumers can key a flash animation */
  tick: number;
}

interface PriceContextValue {
  prices: Record<string, LivePrice>;
  status: ConnectionStatus;
}

const PriceContext = createContext<PriceContextValue>({ prices: {}, status: "connecting" });

export function PriceProvider({ children }: { children: React.ReactNode }) {
  const [prices, setPrices] = useState<Record<string, LivePrice>>({});
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const everConnectedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const es = new EventSource(sseUrl("/api/stream/prices"));

    es.onopen = () => {
      if (cancelled) return;
      everConnectedRef.current = true;
      setStatus("connected");
    };

    es.onmessage = (event) => {
      if (cancelled) return;
      try {
        const update: PriceUpdateEvent = JSON.parse(event.data);
        setPrices((prev) => {
          const prevTick = prev[update.ticker]?.tick ?? 0;
          return {
            ...prev,
            [update.ticker]: {
              ticker: update.ticker,
              price: update.price,
              previousPrice: update.previous_price,
              timestamp: update.timestamp,
              direction: update.change_direction,
              tick: prevTick + 1,
            },
          };
        });
        setStatus("connected");
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      if (cancelled) return;
      if (es.readyState === EventSource.CLOSED) {
        setStatus("disconnected");
        return;
      }
      // EventSource retries automatically; reflect that in the UI.
      setStatus(everConnectedRef.current ? "reconnecting" : "connecting");
    };

    return () => {
      cancelled = true;
      es.close();
    };
  }, []);

  return <PriceContext.Provider value={{ prices, status }}>{children}</PriceContext.Provider>;
}

export function usePrices(): PriceContextValue {
  return useContext(PriceContext);
}
