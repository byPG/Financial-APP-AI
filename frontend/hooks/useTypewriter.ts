"use client";

import { useEffect, useState } from "react";

const CHARS_PER_TICK = 3;
const TICK_MS = 16;

/** Client-side typewriter effect for assistant chat text (planning/PLAN.md
 * Section 9, Transport & Streaming — the backend returns the complete
 * message in one response; "streaming" is purely a frontend animation). */
export function useTypewriter(fullText: string, enabled: boolean): string {
  const [visible, setVisible] = useState(enabled ? "" : fullText);

  useEffect(() => {
    if (!enabled) {
      setVisible(fullText);
      return;
    }
    setVisible("");
    let i = 0;
    const interval = setInterval(() => {
      i += CHARS_PER_TICK;
      setVisible(fullText.slice(0, i));
      if (i >= fullText.length) {
        clearInterval(interval);
      }
    }, TICK_MS);
    return () => clearInterval(interval);
  }, [fullText, enabled]);

  return visible;
}
