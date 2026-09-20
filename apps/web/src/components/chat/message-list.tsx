import { MessageBubble } from "@/components/chat/message-bubble";
import type { ChatMessage } from "@/types/chat";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="flex flex-col gap-3">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
