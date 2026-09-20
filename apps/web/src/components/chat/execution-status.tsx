import { Loader2, Pause, Play, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ExecutionIndicatorState } from "@/types/dashboard";

const STATE_CONFIG: Record<
  ExecutionIndicatorState,
  { label: string; tone: "neutral" | "accent" | "info" | "warning" | "danger"; icon: typeof Play }
> = {
  idle: { label: "Idle", tone: "neutral", icon: Pause },
  planning: { label: "Planning", tone: "info", icon: Loader2 },
  awaiting_approval: { label: "Awaiting approval", tone: "warning", icon: ShieldAlert },
  running: { label: "Running", tone: "accent", icon: Play },
  stopped: { label: "Stopped", tone: "neutral", icon: Pause },
};

export function ExecutionStatus({ state }: { state: ExecutionIndicatorState }) {
  const config = STATE_CONFIG[state];
  const Icon = config.icon;

  return (
    <Badge tone={config.tone}>
      <Icon
        size={12}
        className={state === "planning" ? "animate-spin" : ""}
        aria-hidden="true"
      />
      {config.label}
    </Badge>
  );
}
