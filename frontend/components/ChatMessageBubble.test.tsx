import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatMessageBubble from "./ChatMessageBubble";
import type { ChatMessage } from "@/types/api";

const message: ChatMessage = {
  id: "1",
  role: "assistant",
  content: "Hello there",
  actions: null,
  created_at: "2026-08-19T00:00:00Z",
};

describe("ChatMessageBubble", () => {
  it("renders full text immediately when animate is false", () => {
    render(<ChatMessageBubble message={message} animate={false} />);
    expect(screen.getByText("Hello there")).toBeInTheDocument();
  });

  it("streams text in progressively when animate is true", async () => {
    render(<ChatMessageBubble message={message} animate />);
    await waitFor(() => expect(screen.getByText("Hello there")).toBeInTheDocument());
  });

  it("renders inline action badges for a trade", () => {
    render(
      <ChatMessageBubble
        message={{
          ...message,
          actions: {
            trades: [{ ticker: "AAPL", side: "buy", quantity: 5, status: "executed", error: null }],
            watchlist_changes: [],
          },
        }}
        animate={false}
      />
    );
    expect(screen.getByText(/buy 5 AAPL/)).toBeInTheDocument();
  });
});
