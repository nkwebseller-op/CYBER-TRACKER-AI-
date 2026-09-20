import { AlertCircle, CircleDot, Loader2 } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";

export type ConversationPhase = "idle" | "processing" | "error";

const CONFIG: Record<ConversationPhase, { label: string; tone: BadgeTone; icon: typeof Loader2 }> = {
  idle: { label: "Idle", tone: "neutral", icon: CircleDot },
  processing: { label: "Processing", tone: "info", icon: Loader2 },
  error: { label: "Error", tone: "danger", icon: AlertCircle },
};

export function ConversationStatus({ phase }: { phase: ConversationPhase }) {
  const config = CONFIG[phase];
  const Icon = config.icon;
  return (
    <Badge tone={config.tone}>
      <Icon size={12} className={phase === "processing" ? "animate-spin" : ""} aria-hidden="true" />
      {config.label}
    </Badge>
  );
}
