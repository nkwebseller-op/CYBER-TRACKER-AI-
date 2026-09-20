/**
 * ChatService: the frontend's contract for POST /api/chat/message.
 *
 * MockChatService below satisfies this interface entirely locally (no
 * network call, no API key of any kind — nothing Gemini-related is ever
 * reachable from the browser). When the real endpoint exists, a
 * HttpChatService implementing the same interface can replace
 * MockChatService in one place (see components/chat/chat-panel.tsx) with
 * no changes to any component.
 */

import { generateLocalId } from "@/lib/chat/id";
import { MockIntentExtractor, type IntentExtractor } from "@/lib/chat/intent-extractor";
import { buildTaskPlan, MISSING_INFO_LABEL, TASK_PLAN_STATUS_LABEL } from "@/lib/chat/task-planner";
import type { ChatMessage, ChatMessageRequest, ChatMessageResponse, TaskPlan } from "@/types/chat";
import { ChatServiceError } from "@/types/chat";

export interface ChatService {
  sendMessage(request: ChatMessageRequest): Promise<ChatMessageResponse>;
}

const MOCK_LATENCY_MS = 700;
const MAX_MESSAGE_LENGTH = 4000;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function buildAssistantReply(taskPlan: TaskPlan): string {
  const { taskIntent } = taskPlan;
  const lines: string[] = [];

  lines.push(
    taskIntent.objective === "unknown"
      ? "I didn't catch an objective in that message — could you describe the authorized security task you'd like me to plan?"
      : `Understood. I've captured this as a candidate ${taskIntent.requestedAction === "unknown" ? "task" : taskIntent.requestedAction.replace("_", " ")}.`
  );

  if (taskIntent.missingInformation.length > 0) {
    const missing = taskIntent.missingInformation.map((field) => MISSING_INFO_LABEL[field]);
    lines.push(`Before I can plan further, I need: ${missing.join(", ")}.`);
  } else {
    lines.push("I have enough to draft a plan, but it still requires your explicit approval before anything runs.");
  }

  lines.push(`Current status: ${TASK_PLAN_STATUS_LABEL[taskPlan.status]}.`);
  return lines.join(" ");
}

/**
 * Deterministic, local implementation. Uses an IntentExtractor to build a
 * TaskIntent and a TaskPlan preview — it never executes, scans, installs,
 * or contacts any external system.
 */
export class MockChatService implements ChatService {
  private readonly extractor: IntentExtractor;

  constructor(extractor: IntentExtractor = new MockIntentExtractor()) {
    this.extractor = extractor;
  }

  async sendMessage(request: ChatMessageRequest): Promise<ChatMessageResponse> {
    const trimmed = request.message.trim();

    if (trimmed.length === 0) {
      throw new ChatServiceError("empty_message", "Message cannot be empty.");
    }
    if (trimmed.length > MAX_MESSAGE_LENGTH) {
      throw new ChatServiceError(
        "invalid_input",
        `Message is too long (limit is ${MAX_MESSAGE_LENGTH} characters).`
      );
    }

    await wait(MOCK_LATENCY_MS);

    const intent = this.extractor.extract(trimmed);
    const taskPlan = buildTaskPlan(request.conversationId, intent);

    const message: ChatMessage = {
      id: generateLocalId("msg"),
      role: "assistant",
      content: buildAssistantReply(taskPlan),
      timestamp: new Date().toISOString(),
      status: "completed",
    };

    return { message, taskIntent: intent, taskPlan, status: "ok" };
  }
}
