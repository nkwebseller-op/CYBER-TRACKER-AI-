import { ChatPanel } from "@/components/chat/chat-panel";

export default function ChatPage() {
  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Chat / Command Center</h1>
        <p className="text-sm text-muted">
          Natural-language entry point for authorized security objectives.
        </p>
      </div>
      <div className="flex-1">
        <ChatPanel />
      </div>
    </div>
  );
}
