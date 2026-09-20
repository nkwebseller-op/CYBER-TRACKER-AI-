/**
 * Builds a TaskPlan preview from a TaskIntent. Purely presentational
 * planning data — nothing here schedules or executes work. Compare to
 * services/agent (server-side Task Planner) which will eventually produce
 * the real PlannedAction objects that go through services/policy/engine.py.
 */

import { generateLocalId } from "@/lib/chat/id";
import type { WorkflowStage, WorkflowStageKey } from "@/types/dashboard";
import type { TaskIntent, TaskPlan, TaskPlanStatus } from "@/types/chat";

const STAGE_ORDER: Array<{ key: WorkflowStageKey; label: string }> = [
  { key: "UNDERSTAND", label: "Understand" },
  { key: "RESEARCH", label: "Research" },
  { key: "SELECT", label: "Select" },
  { key: "APPROVE", label: "Approve" },
  { key: "PREPARE", label: "Prepare" },
  { key: "RUN", label: "Run" },
  { key: "ANALYZE", label: "Analyze" },
  { key: "REPORT", label: "Report" },
];

function buildWorkflow(intent: TaskIntent): WorkflowStage[] {
  const hasMissingInfo = intent.missingInformation.length > 0;

  return STAGE_ORDER.map(({ key, label }, index) => {
    if (index === 0) {
      return { key, label, status: hasMissingInfo ? "active" : "complete" };
    }
    if (index === 1 && !hasMissingInfo) {
      return { key, label, status: "active" };
    }
    return { key, label, status: "pending" };
  });
}

function deriveStatus(intent: TaskIntent): TaskPlanStatus {
  if (intent.missingInformation.length > 0) return "WAITING_FOR_INFORMATION";
  if (intent.authorizationStatus !== "AUTHORIZED") return "AWAITING_AUTHORIZATION";
  return "READY_FOR_APPROVAL";
}

export function buildTaskPlan(conversationId: string, intent: TaskIntent): TaskPlan {
  return {
    id: generateLocalId("plan"),
    conversationId,
    taskIntent: intent,
    workflow: buildWorkflow(intent),
    status: deriveStatus(intent),
    createdAt: new Date().toISOString(),
  };
}

export const TASK_PLAN_STATUS_LABEL: Record<TaskPlanStatus, string> = {
  WAITING_FOR_INFORMATION: "Waiting for required information",
  AWAITING_AUTHORIZATION: "Awaiting authorization confirmation",
  READY_FOR_APPROVAL: "Ready for approval",
};

export const MISSING_INFO_LABEL: Record<TaskIntent["missingInformation"][number], string> = {
  target: "Target not specified",
  authorization: "Authorization not confirmed",
  scope: "Scope not defined",
  environment: "Environment not specified",
};
