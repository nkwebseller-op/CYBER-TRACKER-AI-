import { ShieldAlert, ShieldCheck, ShieldQuestion, ShieldX } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import type { AuthorizationState } from "@/types/chat";

const CONFIG: Record<AuthorizationState, { label: string; tone: BadgeTone; icon: typeof ShieldCheck }> = {
  UNKNOWN: { label: "Authorization Unknown", tone: "neutral", icon: ShieldQuestion },
  PENDING: { label: "Authorization Pending", tone: "warning", icon: ShieldAlert },
  AUTHORIZED: { label: "Authorized", tone: "accent", icon: ShieldCheck },
  NOT_AUTHORIZED: { label: "Not Authorized", tone: "danger", icon: ShieldX },
};

export function AuthorizationBadge({ state }: { state: AuthorizationState }) {
  const config = CONFIG[state];
  const Icon = config.icon;
  return (
    <Badge tone={config.tone}>
      <Icon size={12} aria-hidden="true" />
      {config.label}
    </Badge>
  );
}
