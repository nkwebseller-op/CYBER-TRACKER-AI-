/**
 * Real backend implementation of ChatService — POST /api/chat/message
 * (see apps/api/app/api/routes/chat.py). No AI provider or API key logic
 * lives here or anywhere else in the frontend; this is a plain HTTP call
 * whose response shape is validated server-side before it ever reaches
 * this file (see services/agent/chat_pipeline.py).
 *
 * Selected via NEXT_PUBLIC_CHAT_PROVIDER=http (see get-chat-service.ts).
 * Defaults to MockChatService so local UI development never depends on a
 * configured backend or spends real AI provider credits.
 */

import { API_BASE_URL } from "@/lib/api";
import type { ChatService } from "@/lib/chat/chat-service";
import type { ChatErrorCode, ChatMessageRequest, ChatMessageResponse } from "@/types/chat";
import { ChatServiceError } from "@/types/chat";

const KNOWN_ERROR_CODES: ChatErrorCode[] = [
  "empty_message",
  "invalid_input",
  "request_failed",
  "timeout",
  "invalid_task",
  "unexpected_response",
];

function isKnownErrorCode(value: unknown): value is ChatErrorCode {
  return typeof value === "string" && (KNOWN_ERROR_CODES as string[]).includes(value);
}

export class HttpChatService implements ChatService {
  async sendMessage(request: ChatMessageRequest): Promise<ChatMessageResponse> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
    } catch {
      throw new ChatServiceError("request_failed", "Could not reach Cyber AI. Please try again.");
    }

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body?.detail;
      const code = isKnownErrorCode(detail?.code) ? detail.code : "request_failed";
      const message =
        typeof detail?.message === "string" ? detail.message : "Cyber AI could not process that message.";
      throw new ChatServiceError(code, message);
    }

    const body = (await response.json()) as ChatMessageResponse;
    if (!body || typeof body !== "object" || !body.message || !body.taskPlan) {
      throw new ChatServiceError("unexpected_response", "Received an unexpected response from Cyber AI.");
    }

    return body;
  }
}
