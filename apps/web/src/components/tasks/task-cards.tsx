import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { formatDuration, formatRelativeDate, titleCase } from "@/lib/format";
import type { Task } from "@/types/dashboard";

export function TaskCards({
  tasks,
  onSelect,
}: {
  tasks: Task[];
  onSelect: (task: Task) => void;
}) {
  return (
    <div className="space-y-3 md:hidden">
      {tasks.map((task) => (
        <button
          key={task.id}
          onClick={() => onSelect(task)}
          className="motion-safe-transition w-full rounded-md border border-border bg-surface-raised/50 p-4 text-left hover:border-border-strong"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="font-mono text-xs text-muted">{task.id}</p>
            <TaskStatusBadge status={task.status} />
          </div>
          <p className="mt-1 text-sm text-foreground">{task.objective}</p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt className="text-muted">Target</dt>
              <dd className="text-muted-strong">{task.targetName}</dd>
            </div>
            <div>
              <dt className="text-muted">Stage</dt>
              <dd className="text-muted-strong">{titleCase(task.stage)}</dd>
            </div>
            <div>
              <dt className="text-muted">Started</dt>
              <dd className="text-muted-strong">{formatRelativeDate(task.startedAt)}</dd>
            </div>
            <div>
              <dt className="text-muted">Duration</dt>
              <dd className="text-muted-strong">{formatDuration(task.durationSeconds)}</dd>
            </div>
          </dl>
        </button>
      ))}
    </div>
  );
}
