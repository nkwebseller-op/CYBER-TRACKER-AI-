/**
 * Chat / Command Center domain types (Phase 3).
 *
 * These model the conceptual pipeline in docs/ARCHITECTURE.md:
 *   user message -> intent extraction -> structured task intent
 *   -> policy/authorization placeholder -> task plan preview
 *   -> ready for future execution.
 *
 * Nothing here executes anything. TaskIntent/TaskPlan are plain data —
 * the same shape a real backend (services/agent + services/policy) would
 * eventually produce, so swapping the mock ChatService for a real
 * `POST /api/chat/message` call (see lib/chat/chat-service.ts) requires
 * no changes to these types or to the components that render them.
 */

import type { WorkflowStage } from "@/types/dashboard";

export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "sending" | "processing" | "completed" | "failed" | "cancelled";

export type ChatErrorCode =
  | "empty_message"
  | "invalid_input"
  | "request_failed"
  | "timeout"
  | "invalid_task"
  | "unexpected_response";

export interface TaskStatusMetadata {
  kind: "task_status";
  taskPlanId: string;
  stageLabel: string;
}

export interface ErrorMetadata {
  kind: "error";
  code: ChatErrorCode;
}

export type ChatMessageMetadata = TaskStatusMetadata | ErrorMetadata;

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  status: MessageStatus;
  metadata?: ChatMessageMetadata;
}

export type TargetType =
  | "web_application"
  | "api"
  | "server"
  | "cloud_resource"
  | "mobile_device"
  | "wireless_device"
  | "network_asset"
  | "unknown";

/** Never set to AUTHORIZED by client-side parsing — only a real policy/
 * authorization check (Phase 4+) may do that. See IntentExtractor. */
export type AuthorizationState = "UNKNOWN" | "PENDING" | "AUTHORIZED" | "NOT_AUTHORIZED";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export type ApprovalRequirement = "NO_APPROVAL_REQUIRED" | "APPROVAL_REQUIRED";

export type MissingInfoField = "target" | "authorization" | "scope" | "environment";

export interface TaskIntent {
  id: string;
  objective: string;
  target: string | "unknown";
  targetType: TargetType;
  requestedAction: string | "unknown";
  constraints: string[];
  authorizationStatus: AuthorizationState;
  riskLevel: RiskLevel;
  requiresApproval: ApprovalRequirement;
  missingInformation: MissingInfoField[];
}

export type TaskPlanStatus =
  | "WAITING_FOR_INFORMATION"
  | "AWAITING_AUTHORIZATION"
  | "READY_FOR_APPROVAL";

export interface TaskPlan {
  id: string;
  conversationId: string;
  taskIntent: TaskIntent;
  workflow: WorkflowStage[];
  status: TaskPlanStatus;
  createdAt: string;
}

/**
 * Backend contract for POST /api/chat/message. The mock ChatService
 * implements this shape locally; a real implementation only needs to
 * satisfy the same interface (see lib/chat/chat-service.ts).
 */
export interface ChatMessageRequest {
  conversationId: string;
  message: string;
}

export interface ChatMessageResponse {
  message: ChatMessage;
  taskIntent: TaskIntent | null;
  taskPlan: TaskPlan | null;
  status: "ok" | "error";
}

/**
 * Streaming preparation (Phase 3 scope: types + a local event bus only —
 * no fake character-by-character rendering). A future streaming backend
 * publishes these same event names over a WebSocket; the UI subscribes
 * the same way regardless of transport.
 */
export type ChatStreamEvent =
  | { type: "response.started"; conversationId: string; messageId: string }
  | { type: "response.delta"; conversationId: string; messageId: string; delta: string }
  | { type: "response.completed"; conversationId: string; message: ChatMessage }
  | { type: "task.updated"; conversationId: string; taskPlan: TaskPlan }
  | { type: "task.failed"; conversationId: string; reason: string };

export class ChatServiceError extends Error {
  code: ChatErrorCode;

  constructor(code: ChatErrorCode, message: string) {
    super(message);
    this.name = "ChatServiceError";
    this.code = code;
  }
}
