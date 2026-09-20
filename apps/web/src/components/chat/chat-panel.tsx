"use client";

import { useState } from "react";
import { CommandInput } from "@/components/chat/command-input";
import { ExecutionStatus } from "@/components/chat/execution-status";
import { MessageList } from "@/components/chat/message-list";
import { MOCK_CHAT_HISTORY } from "@/lib/mock";
import type { ChatUIMessage, ExecutionIndicatorState } from "@/types/dashboard";

let messageCounter = 0;
function nextId(): string {
  messageCounter += 1;
  return `local-${messageCounter}`;
}

function nowLabel(): string {
  return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/**
 * Phase 2 scope: this panel simulates the conversation with canned,
 * locally-generated responses. It does not call the AI Orchestrator or
 * any execution path — see docs/PHASE_1.md and services/agent for where
 * the real orchestrator lives when this is wired up in a later phase.
 */
export function ChatPanel() {
  const [messages, setMessages] = useState<ChatUIMessage[]>(MOCK_CHAT_HISTORY);
  const [executionState, setExecutionState] = useState<ExecutionIndicatorState>(
    "awaiting_approval"
  );
  const [isThinking, setIsThinking] = useState(false);

  function handleSend(content: string) {
    const userMessage: ChatUIMessage = {
      id: nextId(),
      role: "user",
      content,
      timestamp: nowLabel(),
      status: "sent",
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);
    setExecutionState("planning");

    window.setTimeout(() => {
      const reply: ChatUIMessage = {
        id: nextId(),
        role: "assistant",
        content:
          "This is a simulated response for Phase 2 (UI only). Once the Task Planner is wired up, I'll turn this objective into a structured action and route it through the Policy Engine before anything can run.",
        timestamp: nowLabel(),
        status: "sent",
      };
      setMessages((prev) => [...prev, reply]);
      setIsThinking(false);
      setExecutionState("awaiting_approval");
    }, 900);
  }

  function handleStop() {
    setIsThinking(false);
    setExecutionState("stopped");
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted">
          Simulated conversation — no objective is planned or executed yet.
        </p>
        <ExecutionStatus state={executionState} />
      </div>

      <div className="scrollbar-thin flex-1 space-y-3 overflow-y-auto rounded-lg border border-border bg-surface p-4">
        <MessageList messages={messages} />
        {isThinking && (
          <p className="animate-fade-in-up text-xs text-muted" role="status">
            AI Orchestrator is thinking…
          </p>
        )}
      </div>

      <CommandInput
        onSubmit={handleSend}
        disabled={isThinking}
        isRunning={isThinking}
        onStop={handleStop}
      />
    </div>
  );
}
