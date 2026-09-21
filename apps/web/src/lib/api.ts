export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://cyber-ai-api-production.up.railway.app";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  model: string;
  provider: string;
}

export async function postChat(messages: ChatMessage[]): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Chat request failed (${response.status})`);
  }

  return response.json();
}
