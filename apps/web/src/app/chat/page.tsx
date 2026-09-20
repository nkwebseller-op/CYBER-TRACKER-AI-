import { ChatPanel } from "@/components/chat/chat-panel";
import { PageHeader } from "@/components/ui/page-header";

export default function ChatPage() {
  return (
    <div className="flex h-full flex-col gap-4">
      <PageHeader
        title="Chat / Command Center"
        description="Describe an authorized security objective in natural language. Cyber AI drafts a task plan for your review — nothing is researched, approved, or executed automatically."
      />
      <div className="min-h-0 flex-1">
        <ChatPanel />
      </div>
    </div>
  );
}
