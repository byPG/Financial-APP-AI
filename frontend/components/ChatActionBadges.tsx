"use client";

import type { ChatActions } from "@/types/api";

export default function ChatActionBadges({ actions }: { actions: ChatActions | null }) {
  if (!actions || (actions.trades.length === 0 && actions.watchlist_changes.length === 0)) {
    return null;
  }

  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {actions.trades.map((t, i) => (
        <span
          key={`trade-${i}`}
          className={`rounded border px-1.5 py-0.5 text-[11px] font-mono ${
            t.status === "executed"
              ? "border-up/40 bg-up/10 text-up"
              : "border-down/40 bg-down/10 text-down"
          }`}
          title={t.error ?? undefined}
        >
          {t.status === "executed" ? "✓" : "✕"} {t.side} {t.quantity} {t.ticker}
        </span>
      ))}
      {actions.watchlist_changes.map((w, i) => (
        <span
          key={`wl-${i}`}
          className={`rounded border px-1.5 py-0.5 text-[11px] font-mono ${
            w.status === "executed"
              ? "border-blue-primary/40 bg-blue-primary/10 text-blue-primary"
              : "border-down/40 bg-down/10 text-down"
          }`}
          title={w.error ?? undefined}
        >
          {w.status === "executed" ? "✓" : "✕"} {w.action} {w.ticker}
        </span>
      ))}
    </div>
  );
}
