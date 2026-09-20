import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { Modal } from "@/components/ui/modal";
import { formatDuration, formatRelativeDate, titleCase } from "@/lib/format";
import type { Task } from "@/types/dashboard";

export function TaskDetailModal({
  task,
  isOpen,
  onClose,
}: {
  task: Task | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!task) return null;

  return (
    <Modal title={task.id} isOpen={isOpen} onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-foreground">{task.objective}</p>

        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-xs text-muted">Target</dt>
            <dd className="mt-0.5 text-foreground">{task.targetName}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Status</dt>
            <dd className="mt-0.5">
              <TaskStatusBadge status={task.status} />
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Workflow Stage</dt>
            <dd className="mt-0.5 text-foreground">{titleCase(task.stage)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Started</dt>
            <dd className="mt-0.5 text-foreground">{formatRelativeDate(task.startedAt)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Duration</dt>
            <dd className="mt-0.5 text-foreground">{formatDuration(task.durationSeconds)}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-muted">Result</dt>
            <dd className="mt-0.5 text-foreground">{task.result ?? "No result yet."}</dd>
          </div>
        </dl>

        <p className="rounded-md border border-border bg-surface-raised/60 px-3 py-2 text-xs text-muted">
          Full action-by-action detail (planned actions, policy decisions, execution output) will
          appear here once the Task Planner and Execution Controller are wired to real data.
        </p>
      </div>
    </Modal>
  );
}
