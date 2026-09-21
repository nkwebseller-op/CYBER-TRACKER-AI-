/**
 * Selects the ChatService implementation. Defaults to the local mock so
 * running the UI never requires a configured backend or spends AI
 * provider credits — set NEXT_PUBLIC_CHAT_PROVIDER=http to use the real
 * POST /api/chat/message backend once it's configured with a provider.
 */

import { type ChatService, MockChatService } from "@/lib/chat/chat-service";
import { HttpChatService } from "@/lib/chat/http-chat-service";

let cachedService: ChatService | null = null;

export function getChatService(): ChatService {
  if (!cachedService) {
    const provider = process.env.NEXT_PUBLIC_CHAT_PROVIDER ?? "http";
    cachedService = provider === "http" ? new HttpChatService() : new MockChatService();
  }
  return cachedService;
}
