/**
 * IntentExtractor: turns a free-text objective into a structured
 * TaskIntent. This is a clean seam — the Gemini-backed extractor that
 * eventually replaces MockIntentExtractor (see services/agent/orchestrator.py
 * for where that lives server-side) only needs to satisfy this interface.
 *
 * MockIntentExtractor is deterministic keyword matching, not AI. It never
 * invents a target or authorization state it cannot support from the text:
 * target/authorization/scope/environment are left "unknown" (or UNKNOWN)
 * and reported in `missingInformation` rather than guessed.
 */

import { generateLocalId } from "@/lib/chat/id";
import type {
  ApprovalRequirement,
  AuthorizationState,
  MissingInfoField,
  RiskLevel,
  TargetType,
  TaskIntent,
} from "@/types/chat";

export interface IntentExtractor {
  extract(objective: string): TaskIntent;
}

const TARGET_TYPE_KEYWORDS: Array<{ type: TargetType; keywords: string[] }> = [
  { type: "web_application", keywords: ["website", "web app", "web application", "webapp"] },
  { type: "api", keywords: ["api", "endpoint", "rest service", "graphql"] },
  { type: "cloud_resource", keywords: ["cloud", "aws", "azure", "gcp", "s3 bucket", "vpc"] },
  { type: "mobile_device", keywords: ["android", "ios", "mobile device", "mobile app", "phone", "handset"] },
  { type: "wireless_device", keywords: ["bluetooth", "wireless", "wifi", "wi-fi", "ble", "beacon"] },
  { type: "network_asset", keywords: ["network", "lan", "subnet", "vlan", "office network"] },
  { type: "server", keywords: ["server", "vm", "virtual machine", "host", "database server"] },
];

const ACTION_KEYWORDS: Array<{ action: string; keywords: string[] }> = [
  { action: "security_assessment", keywords: ["security issue", "security assessment", "vulnerab", "security of"] },
  { action: "configuration_review", keywords: ["configuration", "config", "hardening", "compliance"] },
  { action: "reconnaissance", keywords: ["reconnaissance", "enumerate", "discover", "scan for"] },
];

const ENVIRONMENT_KEYWORDS = ["production", "staging", "internal", "development", "dev environment"];

// A host-like token: a dotted domain, an IPv4 address, or a bare CIDR range.
const HOST_PATTERN = /\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b|\b\d{1,3}(?:\.\d{1,3}){3}(?:\/\d{1,2})?\b/i;

function matchFirst(text: string, table: Array<{ keywords: string[] }>): number {
  return table.findIndex((entry) => entry.keywords.some((keyword) => text.includes(keyword)));
}

// Takes the already-computed authorization/risk values as parameters (rather
// than inlining the comparison) so a future code path that can actually
// produce AUTHORIZED — a real policy check — doesn't get flagged as
// unreachable by the type checker the way a same-scope literal would be.
function deriveRequiresApproval(
  authorizationStatus: AuthorizationState,
  riskLevel: RiskLevel
): ApprovalRequirement {
  return authorizationStatus === "AUTHORIZED" && riskLevel === "LOW"
    ? "NO_APPROVAL_REQUIRED"
    : "APPROVAL_REQUIRED";
}

export class MockIntentExtractor implements IntentExtractor {
  extract(objectiveRaw: string): TaskIntent {
    const objective = objectiveRaw.trim();
    const normalized = objective.toLowerCase();

    const targetTypeIndex = matchFirst(normalized, TARGET_TYPE_KEYWORDS);
    const targetType: TargetType =
      targetTypeIndex >= 0 ? TARGET_TYPE_KEYWORDS[targetTypeIndex].type : "unknown";

    const hostMatch = objective.match(HOST_PATTERN);
    const target = hostMatch ? hostMatch[0] : "unknown";

    const actionIndex = matchFirst(normalized, ACTION_KEYWORDS);
    const requestedAction = actionIndex >= 0 ? ACTION_KEYWORDS[actionIndex].action : "unknown";

    const hasEnvironment = ENVIRONMENT_KEYWORDS.some((keyword) => normalized.includes(keyword));

    // Authorization is never inferred from wording like "my authorized
    // server" — only a real Target record with active authorization
    // evidence (services/policy/engine.py: TargetScope.is_authorized_now)
    // can establish that. Text parsing always reports UNKNOWN here.
    const authorizationStatus: AuthorizationState = "UNKNOWN";

    const missingInformation: MissingInfoField[] = [];
    if (target === "unknown") missingInformation.push("target");
    missingInformation.push("authorization");
    if (requestedAction === "unknown") missingInformation.push("scope");
    if (!hasEnvironment) missingInformation.push("environment");

    // Risk is a placeholder for the future Policy Engine (see
    // services/policy/engine.py RiskTier) — unauthorized + unscoped work
    // is always treated as at least MEDIUM risk here, never assumed LOW.
    const riskLevel: RiskLevel = objective.length === 0 ? "LOW" : "MEDIUM";
    const requiresApproval = deriveRequiresApproval(authorizationStatus, riskLevel);

    return {
      id: generateLocalId("intent"),
      objective: objective.length > 0 ? objective : "unknown",
      target,
      targetType,
      requestedAction,
      constraints: [],
      authorizationStatus,
      riskLevel,
      requiresApproval,
      missingInformation,
    };
  }
}
