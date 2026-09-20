import type { BadgeTone } from "@/components/ui/badge";
import type {
  AgentState,
  AuthorizationStatus,
  ReportStatus,
  Severity,
  TargetStatus,
  TaskStatus,
  ToolInstallStatus,
  ToolProvenance,
} from "@/types/dashboard";
import type { RiskLevel, TrustStatus } from "@/types/tools";

export const AGENT_STATE_TONE: Record<AgentState, BadgeTone> = {
  ONLINE: "accent",
  READY: "accent",
  RUNNING: "info",
  IDLE: "neutral",
  WARNING: "warning",
  OFFLINE: "danger",
};

export const TASK_STATUS_TONE: Record<TaskStatus, BadgeTone> = {
  QUEUED: "neutral",
  PLANNING: "info",
  RESEARCHING: "info",
  WAITING_APPROVAL: "warning",
  PREPARING: "info",
  RUNNING: "accent",
  ANALYZING: "info",
  COMPLETED: "accent",
  FAILED: "danger",
  CANCELLED: "neutral",
};

export const AUTHORIZATION_TONE: Record<AuthorizationStatus, BadgeTone> = {
  authorized: "accent",
  pending: "warning",
  expired: "danger",
  revoked: "danger",
};

export const TARGET_STATUS_TONE: Record<TargetStatus, BadgeTone> = {
  idle: "neutral",
  scheduled: "info",
  assessing: "accent",
  attention: "warning",
  clear: "accent",
};

export const SEVERITY_TONE: Record<Severity, BadgeTone> = {
  info: "info",
  low: "neutral",
  medium: "warning",
  high: "warning",
  critical: "danger",
};

export const REPORT_STATUS_TONE: Record<ReportStatus, BadgeTone> = {
  draft: "info",
  final: "accent",
  archived: "neutral",
};

export const TOOL_INSTALL_TONE: Record<ToolInstallStatus, BadgeTone> = {
  installed: "accent",
  available: "info",
  installing: "warning",
  unavailable: "neutral",
};

export const TOOL_PROVENANCE_TONE: Record<ToolProvenance, BadgeTone> = {
  official_repo: "accent",
  verified_vendor: "info",
  package_manager: "neutral",
  unverified: "warning",
};

export const TRUST_STATUS_TONE: Record<TrustStatus, BadgeTone> = {
  unknown: "neutral",
  discovered: "neutral",
  under_review: "info",
  verified: "info",
  approved: "accent",
  blocked: "danger",
  deprecated: "danger",
};

export const RISK_LEVEL_TONE: Record<RiskLevel, BadgeTone> = {
  low: "accent",
  medium: "info",
  high: "warning",
  critical: "danger",
};
