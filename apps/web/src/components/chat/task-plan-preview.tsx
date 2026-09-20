import { AlertCircle, Check } from "lucide-react";
import { AuthorizationBadge } from "@/components/chat/authorization-badge";
import { ApprovalBadge, RiskBadge } from "@/components/chat/risk-badge";
import { Panel } from "@/components/ui/panel";
import { MISSING_INFO_LABEL, TASK_PLAN_STATUS_LABEL } from "@/lib/chat/task-planner";
import { titleCase } from "@/lib/format";
import type { TaskPlan } from "@/types/chat";
import type { WorkflowStageStatus } from "@/types/dashboard";

const STAGE_STYLES: Record<WorkflowStageStatus, string> = {
  complete: "border-accent-soft/50 bg-accent-soft/15 text-accent",
  active: "border-accent bg-accent/10 text-accent",
  pending: "border-border bg-surface-raised/40 text-muted",
  blocked: "border-danger/40 bg-danger-soft text-danger",
};

export function TaskPlanPreview({ plan }: { plan: TaskPlan }) {
  const { taskIntent } = plan;

  return (
    <Panel
      title="Task Plan"
      subtitle="What Cyber AI intends to do before anything is executed"
      className="animate-fade-in-up"
    >
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs text-muted">Objective</p>
            <p className="mt-0.5 text-sm text-foreground">
              {taskIntent.objective === "unknown" ? "Not specified" : taskIntent.objective}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">Target</p>
            <p className="mt-0.5 text-sm text-foreground">
              {taskIntent.target === "unknown" ? "Not specified" : taskIntent.target}
              {taskIntent.targetType !== "unknown" && (
                <span className="text-muted"> · {titleCase(taskIntent.targetType)}</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <AuthorizationBadge state={taskIntent.authorizationStatus} />
          <RiskBadge level={taskIntent.riskLevel} />
          <ApprovalBadge requirement={taskIntent.requiresApproval} />
        </div>

        {taskIntent.missingInformation.length > 0 && (
          <div className="rounded-md border border-warning/30 bg-warning-soft px-3.5 py-3">
            <div className="flex items-center gap-2 text-xs font-medium text-warning">
              <AlertCircle size={14} aria-hidden="true" />
              Missing information
            </div>
            <ul className="mt-2 space-y-1 pl-1 text-xs text-muted-strong">
              {taskIntent.missingInformation.map((field) => (
                <li key={field} className="flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-muted" aria-hidden="true" />
                  {MISSING_INFO_LABEL[field]}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className="mb-3 text-xs font-medium text-muted-strong">Planned workflow</p>
          <ol className="flex flex-col gap-3 sm:flex-row sm:gap-2">
            {plan.workflow.map((stage, index) => (
              <li key={stage.key} className="flex flex-1 items-center gap-2 sm:flex-col sm:gap-1.5">
                <div
                  className={`motion-safe-transition flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${STAGE_STYLES[stage.status]} ${
                    stage.status === "active" ? "animate-pulse-dot" : ""
                  }`}
                >
                  {stage.status === "complete" ? (
                    <Check size={12} aria-hidden="true" />
                  ) : (
                    <span aria-hidden="true">{index + 1}</span>
                  )}
                </div>
                <span
                  className={`text-[11px] font-medium sm:text-center ${
                    stage.status === "pending" ? "text-muted" : "text-foreground"
                  }`}
                >
                  {stage.label}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-md border border-border bg-surface-raised/60 px-3.5 py-2.5 text-center text-xs font-medium text-muted-strong">
          Status: {TASK_PLAN_STATUS_LABEL[plan.status].toUpperCase()}
        </div>
      </div>
    </Panel>
  );
}
