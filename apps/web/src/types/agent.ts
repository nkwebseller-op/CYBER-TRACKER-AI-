/** Mirrors apps/api/app/schemas/agent.py (Phase 12). */

export type AgentPhase =
  | "CREATED"
  | "UNDERSTANDING"
  | "RESEARCHING"
  | "PLANNING"
  | "WAITING_FOR_AUTHORIZATION"
  | "WAITING_FOR_APPROVAL"
  | "PREPARING"
  | "EXECUTING"
  | "OBSERVING"
  | "ANALYZING"
  | "VERIFYING"
  | "RECOVERING"
  | "PAUSED"
  | "CANCELLED"
  | "COMPLETED"
  | "FAILED"
  | "BLOCKED";

export type EvidenceKind =
  | "FACT"
  | "OBSERVATION"
  | "ASSUMPTION"
  | "UNKNOWN"
  | "FINDING"
  | "VERIFIED_FINDING";

export interface AgentActionSummary {
  id: string;
  actionType: string;
  tool: string | null;
  capability: string | null;
  requiresApproval: boolean;
  approvalState: "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED";
  resultSummary: string | null;
  errorCategory: string | null;
  confidence: number;
}

export interface EvidenceSummary {
  id: string;
  kind: EvidenceKind;
  summary: string;
}

export interface AgentTask {
  id: string;
  objective: string;
  target: string | null;
  targetType: string | null;
  authorizationStatus: string;
  phase: AgentPhase;
  actions: AgentActionSummary[];
  observations: EvidenceSummary[];
  findings: EvidenceSummary[];
  errors: string[];
  selectedTools: string[];
  confidence: number;
  unknowns: string[];
  clarificationQuestion: string | null;
  pendingActionId: string | null;
  budget: Record<string, number>;
  createdAt: string;
  updatedAt: string;
}

export interface AgentEvent {
  id: string;
  eventType: string;
  data: Record<string, unknown>;
  createdAt: string;
}

/** Compact workflow visualization stages (Phase 12 §16). */
export const AGENT_WORKFLOW_STAGES = [
  "UNDERSTAND",
  "RESEARCH",
  "PLAN",
  "APPROVE",
  "PREPARE",
  "EXECUTE",
  "ANALYZE",
  "VERIFY",
  "REPORT",
] as const;

export type AgentWorkflowStage = (typeof AGENT_WORKFLOW_STAGES)[number];

export const AGENT_PHASE_TO_WORKFLOW_STAGE: Record<AgentPhase, AgentWorkflowStage> = {
  CREATED: "UNDERSTAND",
  UNDERSTANDING: "UNDERSTAND",
  RESEARCHING: "RESEARCH",
  PLANNING: "PLAN",
  WAITING_FOR_AUTHORIZATION: "UNDERSTAND",
  WAITING_FOR_APPROVAL: "APPROVE",
  PREPARING: "PREPARE",
  EXECUTING: "EXECUTE",
  OBSERVING: "EXECUTE",
  ANALYZING: "ANALYZE",
  VERIFYING: "VERIFY",
  RECOVERING: "EXECUTE",
  PAUSED: "EXECUTE",
  CANCELLED: "REPORT",
  COMPLETED: "REPORT",
  FAILED: "REPORT",
  BLOCKED: "REPORT",
};
