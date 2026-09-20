"use client";

import { useState } from "react";
import { postChat, type ChatMessage } from "@/lib/api";

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const objective = input.trim();
    if (!objective || isSending) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: objective }];
    setMessages(nextMessages);
    setInput("");
    setIsSending(true);
    setError(null);

    try {
      const response = await postChat(nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: response.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-border bg-surface p-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted">
            Describe an authorized security objective, e.g. &ldquo;Assess the security of my
            authorized web server.&rdquo; This phase only holds a conversation — no actions are
            planned or executed yet.
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={
              message.role === "user"
                ? "ml-auto max-w-[80%] rounded-lg bg-accent-dim/30 px-3 py-2 text-sm text-foreground"
                : "max-w-[80%] rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-foreground"
            }
          >
            {message.content}
          </div>
        ))}
        {isSending && <p className="text-xs text-muted">AI Orchestrator is thinking…</p>}
        {error && <p className="text-xs text-danger">{error}</p>}
      </div>
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Describe your authorized objective…"
          className="flex-1 rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={isSending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
