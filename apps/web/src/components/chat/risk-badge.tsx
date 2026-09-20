import { Badge, type BadgeTone } from "@/components/ui/badge";
import type { ApprovalRequirement, RiskLevel } from "@/types/chat";

const RISK_TONE: Record<RiskLevel, BadgeTone> = {
  LOW: "accent",
  MEDIUM: "warning",
  HIGH: "danger",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <Badge tone={RISK_TONE[level]}>{level} Risk</Badge>;
}

export function ApprovalBadge({ requirement }: { requirement: ApprovalRequirement }) {
  return (
    <Badge tone={requirement === "APPROVAL_REQUIRED" ? "warning" : "accent"}>
      {requirement === "APPROVAL_REQUIRED" ? "Approval Required" : "No Approval Required"}
    </Badge>
  );
}
