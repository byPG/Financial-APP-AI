"use client";

import ChatActionBadges from "@/components/ChatActionBadges";
import { useTypewriter } from "@/hooks/useTypewriter";
import type { ChatMessage } from "@/types/api";

export default function ChatMessageBubble({
  message,
  animate,
}: {
  message: ChatMessage;
  animate: boolean;
}) {
  const isUser = message.role === "user";
  const text = useTypewriter(message.content, animate);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser ? "bg-blue-primary/20 text-gray-100" : "bg-bg-raised text-gray-200"
        }`}
      >
        <p className="whitespace-pre-wrap">{text}</p>
        {!isUser && <ChatActionBadges actions={message.actions} />}
      </div>
    </div>
  );
}
