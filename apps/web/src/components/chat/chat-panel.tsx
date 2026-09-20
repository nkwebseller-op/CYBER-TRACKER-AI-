"use client";

import { useMemo, useRef, useState } from "react";
import { ChatEmptyState } from "@/components/chat/chat-empty-state";
import { ChatToolbar } from "@/components/chat/chat-toolbar";
import { CommandInput } from "@/components/chat/command-input";
import { ConversationStatus, type ConversationPhase } from "@/components/chat/conversation-status";
import { ErrorBanner } from "@/components/chat/error-banner";
import { MessageList } from "@/components/chat/message-list";
import { TaskPlanPreview } from "@/components/chat/task-plan-preview";
import { createChatEventBus } from "@/lib/chat/event-bus";
import { generateLocalId } from "@/lib/chat/id";
import { MockChatService } from "@/lib/chat/chat-service";
import type { ChatMessage, TaskPlan } from "@/types/chat";
import { ChatServiceError } from "@/types/chat";

/**
 * Phase 3: the AI Command Center. `chatService` is the only seam between
 * this component and "the backend" — see lib/chat/chat-service.ts. Swap
 * MockChatService for an HTTP-backed implementation of the same
 * ChatService interface when POST /api/chat/message exists; nothing in
 * this component needs to change.
 */
const chatService = new MockChatService();
const eventBus = createChatEventBus();

function createConversationId(): string {
  return generateLocalId("conv");
}

export function ChatPanel() {
  const [conversationId, setConversationId] = useState(createConversationId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [taskPlan, setTaskPlan] = useState<TaskPlan | null>(null);
  const [phase, setPhase] = useState<ConversationPhase>("idle");
  const [error, setError] = useState<{ code: string; message?: string } | null>(null);
  const [draft, setDraft] = useState("");
  const cancelledRef = useRef(false);

  const isProcessing = phase === "processing";

  async function handleSend(content: string) {
    setError(null);

    const userMessage: ChatMessage = {
      id: generateLocalId("msg"),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      status: "completed",
    };
    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setPhase("processing");
    cancelledRef.current = false;

    eventBus.publish({
      type: "response.started",
      conversationId,
      messageId: generateLocalId("stream"),
    });

    try {
      const response = await chatService.sendMessage({ conversationId, message: content });

      if (cancelledRef.current) return;

      setMessages((prev) => [...prev, response.message]);

      if (response.taskPlan) {
        setTaskPlan(response.taskPlan);
        eventBus.publish({
          type: "task.updated",
          conversationId,
          taskPlan: response.taskPlan,
        });

        const statusMessage: ChatMessage = {
          id: generateLocalId("status"),
          role: "system",
          content: `Task plan updated — currently at "${response.taskPlan.workflow.find((s) => s.status === "active")?.label ?? response.taskPlan.workflow[0].label}".`,
          timestamp: new Date().toISOString(),
          status: "completed",
          metadata: { kind: "task_status", taskPlanId: response.taskPlan.id, stageLabel: response.taskPlan.status },
        };
        setMessages((prev) => [...prev, statusMessage]);
      }

      eventBus.publish({ type: "response.completed", conversationId, message: response.message });
      setPhase("idle");
    } catch (err) {
      if (cancelledRef.current) return;

      const chatError =
        err instanceof ChatServiceError
          ? err
          : new ChatServiceError("unexpected_response", "An unexpected error occurred.");

      setMessages((prev) =>
        prev.map((message) =>
          message.id === userMessage.id ? { ...message, status: "failed" } : message
        )
      );
      setError({ code: chatError.code, message: chatError.message });
      eventBus.publish({ type: "task.failed", conversationId, reason: chatError.message });
      setPhase("error");
    }
  }

  function handleStop() {
    cancelledRef.current = true;
    setMessages((prev) =>
      prev.map((message) =>
        message.status === "completed" || message.status === "failed"
          ? message
          : { ...message, status: "cancelled" }
      )
    );
    setPhase("idle");
  }

  function handleNewTask() {
    setConversationId(createConversationId());
    setMessages([]);
    setTaskPlan(null);
    setError(null);
    setDraft("");
    setPhase("idle");
  }

  function handleClearConversation() {
    setMessages([]);
    setTaskPlan(null);
    setError(null);
  }

  const displayPhase: ConversationPhase = useMemo(() => {
    if (error) return "error";
    return phase === "processing" ? "processing" : "idle";
  }, [phase, error]);

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ChatToolbar
          onNewTask={handleNewTask}
          onClear={handleClearConversation}
          hasMessages={messages.length > 0}
        />
        <ConversationStatus phase={displayPhase} />
      </div>

      <div className="scrollbar-thin flex-1 space-y-3 overflow-y-auto rounded-lg border border-border bg-surface p-4">
        {messages.length === 0 ? (
          <ChatEmptyState onSelectSuggestion={setDraft} />
        ) : (
          <MessageList messages={messages} />
        )}
        {isProcessing && (
          <p className="animate-fade-in-up text-xs text-muted" role="status">
            AI Orchestrator is thinking…
          </p>
        )}
      </div>

      {taskPlan && <TaskPlanPreview plan={taskPlan} />}

      {error && (
        <ErrorBanner code={error.code} message={error.message} onDismiss={() => setError(null)} />
      )}

      <CommandInput
        value={draft}
        onChange={setDraft}
        onSubmit={handleSend}
        disabled={isProcessing}
        isRunning={isProcessing}
        onStop={handleStop}
      />
    </div>
  );
}
