/** Mirrors apps/api/app/schemas/installation.py (Phase 11). */

export type InstallationState =
  | "DISCOVERED"
  | "REVIEWING"
  | "DEPENDENCIES_CHECKING"
  | "WAITING_FOR_APPROVAL"
  | "PREPARING"
  | "INSTALLING"
  | "VERIFYING"
  | "INSTALLED"
  | "FAILED"
  | "BLOCKED"
  | "CANCELLED"
  | "ROLLBACK_REQUIRED";

export interface ReadinessCheck {
  name: string;
  status: "PASS" | "FAIL" | "UNKNOWN";
  detail: string;
  critical: boolean;
}

export interface ReadinessReport {
  ready: boolean;
  checks: ReadinessCheck[];
}

export interface DependencyCheck {
  name: string;
  requiredVersion: string | null;
  foundVersion: string | null;
  status: string;
  note: string;
}

export interface InstallationStep {
  description: string;
  packageManager: string;
  actionType: string;
  packageName: string;
  version: string | null;
}

export interface InstallationPlan {
  toolId: string;
  toolName: string;
  platform: string;
  architecture: string;
  version: string | null;
  packageManager: string;
  dependencies: DependencyCheck[];
  prerequisites: string[];
  requiredPermissions: string[];
  installationSteps: InstallationStep[];
  verificationSteps: string[];
  riskLevel: string;
  approvalRequired: boolean;
  estimatedChanges: string[];
  rollbackInformation: string;
}

export interface InstallationAttempt {
  attemptNumber: number;
  startedAt: string;
  completedAt: string | null;
  exitCode: number | null;
  stdout: string | null;
  stderr: string | null;
  durationSeconds: number | null;
  errorCategory: string | null;
}

export interface InstallationVerification {
  executableFound: boolean | null;
  versionOutput: string | null;
  checks: Record<string, string>;
  verified: boolean;
}

export interface InstallationRequest {
  id: string;
  toolId: string;
  targetId: string | null;
  state: InstallationState;
  plan: InstallationPlan | null;
  approvedBy: string | null;
  approvedAt: string | null;
  rejectionReason: string | null;
  attempts: InstallationAttempt[];
  verification: InstallationVerification | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}
