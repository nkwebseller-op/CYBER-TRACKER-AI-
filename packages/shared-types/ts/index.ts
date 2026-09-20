// Hand-maintained TypeScript mirror of packages/shared-types/schemas/*.json.
// Keep structurally in sync; see README.md for why this isn't codegen'd yet.

export type SecurityDomain =
  | "web"
  | "api"
  | "network"
  | "server_config"
  | "cloud"
  | "wireless"
  | "mobile"
  | "vulnerability"
  | "reconnaissance"
  | "defensive"
  | "other";

export type RiskTier = "low" | "medium" | "high" | "critical";

export interface PlannedAction {
  id: string;
  task_id: string;
  action_type: string;
  domain: SecurityDomain;
  target_id: string;
  risk_tier: RiskTier;
  parameters: Record<string, unknown>;
  rationale?: string;
  created_at: string;
}

export type PolicyVerdict = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface PolicyDecision {
  id: string;
  action_id: string;
  verdict: PolicyVerdict;
  reasons: string[];
  requires_approval: boolean;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  decided_at: string;
}

export type TerminalAdapterName = "linux" | "macos" | "windows" | "termux";

export type ExecutionStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "recovering"
  | "cancelled";

export interface ExecutionResult {
  id: string;
  action_id: string;
  adapter: TerminalAdapterName;
  status: ExecutionStatus;
  exit_code?: number | null;
  stdout?: string | null;
  stderr?: string | null;
  started_at: string;
  finished_at?: string | null;
}

export interface Target {
  id: string;
  name: string;
  scope_type: "domain" | "ip_range" | "host" | "application" | "cloud_account";
  scope_value: string;
  authorization_evidence: string;
  authorized_by: string;
  authorized_at: string;
  expires_at?: string | null;
  is_active: boolean;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "down";
  service: string;
  version: string;
  timestamp: string;
}
