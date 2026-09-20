/**
 * Minimal typed pub/sub for ChatStreamEvent. A real streaming backend
 * would publish these same event names over a WebSocket (see
 * apps/api/app/ws/gateway.py); the UI subscribes identically either way.
 * This phase publishes events locally around the mock ChatService call —
 * it does not fabricate incremental text ("response.delta" is defined but
 * unused until a real streaming provider exists).
 */

import type { ChatStreamEvent } from "@/types/chat";

export type ChatEventHandler = (event: ChatStreamEvent) => void;

export interface ChatEventBus {
  subscribe(handler: ChatEventHandler): () => void;
  publish(event: ChatStreamEvent): void;
}

export function createChatEventBus(): ChatEventBus {
  const handlers = new Set<ChatEventHandler>();

  return {
    subscribe(handler) {
      handlers.add(handler);
      return () => handlers.delete(handler);
    },
    publish(event) {
      for (const handler of handlers) handler(event);
    },
  };
}
