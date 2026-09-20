import { Check } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import type { WorkflowStage, WorkflowStageStatus } from "@/types/dashboard";

const STATUS_STYLES: Record<WorkflowStageStatus, string> = {
  complete: "border-accent-soft/50 bg-accent-soft/15 text-accent",
  active: "border-accent bg-accent/10 text-accent",
  pending: "border-border bg-surface-raised/40 text-muted",
  blocked: "border-danger/40 bg-danger-soft text-danger",
};

export function WorkflowPipeline({ stages }: { stages: WorkflowStage[] }) {
  return (
    <Panel title="Workflow Pipeline" subtitle="Current position for the active task">
      <ol className="flex flex-col gap-3 sm:flex-row sm:gap-2">
        {stages.map((stage, index) => (
          <li key={stage.key} className="flex flex-1 items-center gap-3 sm:flex-col sm:gap-2">
            <div
              className={`motion-safe-transition flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${STATUS_STYLES[stage.status]} ${
                stage.status === "active" ? "animate-pulse-dot" : ""
              }`}
            >
              {stage.status === "complete" ? (
                <Check size={15} aria-hidden="true" />
              ) : (
                <span aria-hidden="true">{index + 1}</span>
              )}
            </div>
            <div className="flex flex-1 items-center gap-2 sm:w-full sm:flex-col sm:gap-1">
              <span
                className={`text-xs font-medium sm:text-center ${
                  stage.status === "pending" ? "text-muted" : "text-foreground"
                }`}
              >
                {stage.label}
                <span className="sr-only"> — {stage.status}</span>
              </span>
              {index < stages.length - 1 && (
                <span
                  aria-hidden="true"
                  className={`hidden h-px flex-1 sm:block sm:w-full ${
                    stage.status === "complete" ? "bg-accent-soft" : "bg-border"
                  }`}
                />
              )}
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
