/**
 * Domain types for the Phase 2 UI. These are shaped to match what
 * apps/api and packages/shared-types will eventually serve (see
 * PlannedAction / PolicyDecision / ExecutionResult in
 * packages/shared-types/ts/index.ts) so swapping mock data for real API
 * calls later doesn't require reshaping components.
 */

export type AgentState = "ONLINE" | "READY" | "RUNNING" | "IDLE" | "WARNING" | "OFFLINE";

export interface AgentStatusEntry {
  id: string;
  name: string;
  description: string;
  state: AgentState;
  detail?: string;
}

export type WorkflowStageKey =
  | "UNDERSTAND"
  | "RESEARCH"
  | "SELECT"
  | "APPROVE"
  | "PREPARE"
  | "RUN"
  | "ANALYZE"
  | "REPORT";

export type WorkflowStageStatus = "pending" | "active" | "complete" | "blocked";

export interface WorkflowStage {
  key: WorkflowStageKey;
  label: string;
  status: WorkflowStageStatus;
}

export type ActivityStatus = "success" | "info" | "warning" | "error";

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: string;
  description: string;
  status: ActivityStatus;
}

export interface OverviewMetric {
  id: string;
  label: string;
  value: number;
  delta?: string;
  trend?: "up" | "down" | "flat";
}

export type TargetType =
  | "web_application"
  | "api"
  | "server"
  | "cloud_resource"
  | "mobile_device"
  | "wireless_device"
  | "network_asset";

export type TargetEnvironment = "production" | "staging" | "development" | "internal";

export type AuthorizationStatus = "authorized" | "pending" | "expired" | "revoked";

export type TargetStatus = "idle" | "scheduled" | "assessing" | "attention" | "clear";

export interface Target {
  id: string;
  name: string;
  type: TargetType;
  environment: TargetEnvironment;
  authorizationStatus: AuthorizationStatus;
  lastAssessment: string | null;
  status: TargetStatus;
  owner: string;
  scopeValue: string;
}

export type TaskStatus =
  | "QUEUED"
  | "PLANNING"
  | "RESEARCHING"
  | "WAITING_APPROVAL"
  | "PREPARING"
  | "RUNNING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface Task {
  id: string;
  objective: string;
  targetName: string;
  status: TaskStatus;
  stage: WorkflowStageKey;
  startedAt: string;
  durationSeconds: number | null;
  result: string | null;
}

export type ToolProvenance = "official_repo" | "package_manager" | "verified_vendor" | "unverified";

export type ToolInstallStatus = "installed" | "available" | "unavailable" | "installing";

export interface DiscoveredTool {
  id: string;
  name: string;
  category: string;
  source: string;
  version: string;
  platforms: string[];
  installStatus: ToolInstallStatus;
  provenance: ToolProvenance;
  description: string;
}

export type TerminalLineKind = "command" | "stdout" | "stderr" | "system";

export interface TerminalLine {
  id: string;
  kind: TerminalLineKind;
  text: string;
  timestamp: string;
}

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface SeveritySummary {
  info: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export type ReportStatus = "draft" | "final" | "archived";

export interface SecurityReport {
  id: string;
  title: string;
  targetName: string;
  assessedAt: string;
  findingsCount: number;
  severitySummary: SeveritySummary;
  status: ReportStatus;
}

// Chat / Command Center types (message model, task intent, task plan,
// streaming events) live in src/types/chat.ts as of Phase 3.
