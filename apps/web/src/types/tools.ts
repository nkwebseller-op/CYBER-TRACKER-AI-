/**
 * Mirrors apps/api/app/schemas/tools.py — the Trusted Tool Registry API
 * contract (Phase 10). Nothing here is directly executable: there is no
 * "run" or "install" field, only descriptive/provenance metadata.
 */

export type ToolCategory =
  | "network_diagnostics"
  | "web_api_testing"
  | "vulnerability_assessment"
  | "dns_domain_analysis"
  | "infrastructure_diagnostics"
  | "cloud_security"
  | "mobile_security"
  | "wireless_diagnostics"
  | "packet_traffic_analysis"
  | "log_analysis"
  | "system_diagnostics"
  | "defensive_monitoring"
  | "osint"
  | "developer_utilities";

export type SourceType =
  | "official_website"
  | "official_github"
  | "official_package_registry"
  | "other_reputable"
  | "unknown";

export type TrustStatus =
  | "unknown"
  | "discovered"
  | "under_review"
  | "verified"
  | "approved"
  | "blocked"
  | "deprecated";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type VerificationResultValue = "verified" | "unverified" | "failed" | "unknown";

export interface Provenance {
  sourceType: SourceType;
  sourceUrl: string | null;
  repositoryUrl: string | null;
  documentationUrl: string | null;
  publisher: string | null;
  discoveredVersion: string | null;
  discoveredAt: string;
}

export interface VerificationReport {
  results: Record<string, VerificationResultValue>;
  notes: Record<string, string>;
  completedAt: string | null;
  overall: VerificationResultValue;
}

export interface RegistryTool {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: ToolCategory;
  capabilities: string[];
  supportedPlatforms: string[];
  provenance: Provenance;
  version: string | null;
  license: string | null;
  installationMethod: string | null;
  entrypoint: string | null;
  dependencies: string[];
  requiredPermissions: string[];
  riskLevel: RiskLevel;
  trustStatus: TrustStatus;
  verification: VerificationReport;
  createdAt: string;
  updatedAt: string;
}

export interface ToolCandidate {
  name: string;
  displayName: string;
  description: string;
  category: ToolCategory;
  capabilities: string[];
  supportedPlatforms: string[];
  provenance: Provenance;
  version: string | null;
  license: string | null;
  installationMethod: string | null;
  dependencies: string[];
  requiredPermissions: string[];
  riskLevel: RiskLevel;
  selectionRationale: string;
}

export interface ToolSelectionProposal {
  requiredCapability: string;
  reason: string;
  expectedPlatforms: string[];
  expectedDependencies: string[];
  verificationRequirements: string[];
  candidates: ToolCandidate[];
}
