"use client";

import type { ConnectionStatus } from "@/context/PriceContext";

const STATUS_META: Record<ConnectionStatus, { color: string; label: string; pulse: boolean }> = {
  connected: { color: "bg-up", label: "Live", pulse: false },
  connecting: { color: "bg-accent-yellow", label: "Connecting", pulse: true },
  reconnecting: { color: "bg-accent-yellow", label: "Reconnecting", pulse: true },
  disconnected: { color: "bg-down", label: "Disconnected", pulse: false },
};

export default function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const meta = STATUS_META[status];
  return (
    <div className="flex items-center gap-2" title={meta.label}>
      <span
        className={`h-2.5 w-2.5 rounded-full ${meta.color} ${meta.pulse ? "pulse-dot" : ""}`}
      />
      <span className="text-xs text-gray-400">{meta.label}</span>
    </div>
  );
}
