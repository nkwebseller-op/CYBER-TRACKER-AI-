import type { ChatUIMessage } from "@/types/dashboard";

const ROLE_STYLES: Record<ChatUIMessage["role"], string> = {
  user: "ml-auto max-w-[85%] sm:max-w-[70%] bg-accent-soft/25 border border-accent-soft/30 text-foreground",
  assistant:
    "max-w-[85%] sm:max-w-[70%] border border-border-strong bg-surface-raised text-foreground",
  system:
    "mx-auto max-w-[90%] border border-border bg-surface/60 text-xs text-muted text-center",
};

export function MessageBubble({ message }: { message: ChatUIMessage }) {
  if (message.role === "system") {
    return (
      <div role="status" className={`animate-fade-in-up rounded-full px-3 py-1.5 ${ROLE_STYLES.system}`}>
        {message.content}
      </div>
    );
  }

  return (
    <div className={`animate-fade-in-up rounded-lg px-3.5 py-2.5 text-sm ${ROLE_STYLES[message.role]}`}>
      <p>{message.content}</p>
      <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted">
        <span>{message.role === "user" ? "You" : "Cyber AI"}</span>
        <span aria-hidden="true">·</span>
        <time>{message.timestamp}</time>
        {message.status === "sending" && <span>sending…</span>}
        {message.status === "error" && <span className="text-danger">failed to send</span>}
      </div>
    </div>
  );
}
