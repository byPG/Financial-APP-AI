"use client";

import { formatCurrency } from "@/lib/format";
import type { LivePrice } from "@/context/PriceContext";

export default function PriceCell({ live }: { live: LivePrice | undefined }) {
  if (!live) {
    return <span className="font-mono text-gray-500">—</span>;
  }
  const flashClass = live.direction === "up" ? "flash-up" : live.direction === "down" ? "flash-down" : "";
  return (
    <span key={live.tick} className={`inline-block rounded px-1.5 py-0.5 font-mono ${flashClass}`}>
      {formatCurrency(live.price)}
    </span>
  );
}
