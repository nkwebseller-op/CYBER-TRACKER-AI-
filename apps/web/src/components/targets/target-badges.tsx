import { Badge } from "@/components/ui/badge";
import { AUTHORIZATION_TONE, TARGET_STATUS_TONE } from "@/lib/status-styles";
import { titleCase } from "@/lib/format";
import type { AuthorizationStatus, TargetStatus } from "@/types/dashboard";

export function AuthorizationBadge({ status }: { status: AuthorizationStatus }) {
  return <Badge tone={AUTHORIZATION_TONE[status]}>{titleCase(status)}</Badge>;
}

export function TargetStatusBadge({ status }: { status: TargetStatus }) {
  return <Badge tone={TARGET_STATUS_TONE[status]}>{titleCase(status)}</Badge>;
}
