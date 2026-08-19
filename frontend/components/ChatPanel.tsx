"use client";

import { useEffect, useRef, useState } from "react";
import ChatMessageBubble from "@/components/ChatMessageBubble";
import { usePortfolio } from "@/context/PortfolioContext";
import { useWatchlist } from "@/context/WatchlistContext";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/types/api";

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newMessageId, setNewMessageId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { applyPortfolio } = usePortfolio();
  const { refresh: refreshWatchlist } = useWatchlist();

  useEffect(() => {
    api
      .getChatHistory()
      .then((res) => setMessages(res.messages))
      .catch(() => setError("Failed to load chat history"));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const optimisticUser: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: text,
      actions: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res = await api.sendChatMessage({ message: text });
      setMessages((prev) => [...prev, res.message]);
      setNewMessageId(res.message.id);
      applyPortfolio(res.portfolio);
      if (res.message.actions?.watchlist_changes.length) {
        refreshWatchlist();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
          AI Assistant
        </h2>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {messages.length === 0 && (
          <p className="text-sm text-gray-500">
            Ask FinAlly about your portfolio, or tell it to buy/sell or manage your watchlist.
          </p>
        )}
        {messages.map((m) => (
          <ChatMessageBubble key={m.id} message={m} animate={m.id === newMessageId} />
        ))}
        {sending && <p className="text-xs text-gray-500">FinAlly is thinking…</p>}
      </div>

      {error && <p className="px-3 pb-1 text-xs text-down">{error}</p>}

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border-muted p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message FinAlly…"
          disabled={sending}
          className="min-w-0 flex-1 rounded border border-border-muted bg-bg-base px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-blue-primary disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded bg-purple-secondary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
