import { AlertTriangle, ListChecks } from "lucide-react";
import type { ChatMessage } from "@/types/chat";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

const ROLE_STYLES: Record<ChatMessage["role"], string> = {
  user: "ml-auto max-w-[85%] sm:max-w-[70%] bg-accent-soft/25 border border-accent-soft/30 text-foreground",
  assistant:
    "max-w-[85%] sm:max-w-[70%] border border-border-strong bg-surface-raised text-foreground",
  system: "mx-auto max-w-[90%] border border-border bg-surface/60 text-xs text-muted text-center",
};

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.metadata?.kind === "task_status") {
    return (
      <div
        role="status"
        className="animate-fade-in-up mx-auto flex max-w-[90%] items-center gap-1.5 rounded-full border border-accent-soft/30 bg-accent-soft/10 px-3 py-1.5 text-xs text-accent"
      >
        <ListChecks size={12} aria-hidden="true" />
        {message.content}
      </div>
    );
  }

  if (message.metadata?.kind === "error") {
    return (
      <div
        role="alert"
        className="animate-fade-in-up mx-auto flex max-w-[90%] items-center gap-1.5 rounded-full border border-danger/30 bg-danger-soft px-3 py-1.5 text-xs text-danger"
      >
        <AlertTriangle size={12} aria-hidden="true" />
        {message.content}
      </div>
    );
  }

  if (message.role === "system") {
    return (
      <div role="status" className={`animate-fade-in-up rounded-full px-3 py-1.5 ${ROLE_STYLES.system}`}>
        {message.content}
      </div>
    );
  }

  const isFailed = message.status === "failed";
  const isCancelled = message.status === "cancelled";

  return (
    <div
      className={`animate-fade-in-up rounded-lg px-3.5 py-2.5 text-sm ${ROLE_STYLES[message.role]} ${
        isFailed ? "border-danger/40" : ""
      } ${isCancelled ? "opacity-60" : ""}`}
    >
      <p className="whitespace-pre-wrap">{message.content}</p>
      <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted">
        <span>{message.role === "user" ? "You" : "Cyber AI"}</span>
        <span aria-hidden="true">·</span>
        <time>{formatTime(message.timestamp)}</time>
        {message.status === "sending" && <span>sending…</span>}
        {message.status === "processing" && <span>processing…</span>}
        {isFailed && <span className="text-danger">failed to send</span>}
        {isCancelled && <span>cancelled</span>}
      </div>
    </div>
  );
}
