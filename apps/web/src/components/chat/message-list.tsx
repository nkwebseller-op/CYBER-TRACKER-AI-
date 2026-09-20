import { MessageBubble } from "@/components/chat/message-bubble";
import type { ChatUIMessage } from "@/types/dashboard";

export function MessageList({ messages }: { messages: ChatUIMessage[] }) {
  return (
    <div className="flex flex-col gap-3">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
