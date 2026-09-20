import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { formatDuration, formatRelativeDate, titleCase } from "@/lib/format";
import type { Task } from "@/types/dashboard";

export function TaskTable({
  tasks,
  onSelect,
}: {
  tasks: Task[];
  onSelect: (task: Task) => void;
}) {
  return (
    <table className="hidden w-full text-left text-sm md:table">
      <caption className="sr-only">Tasks</caption>
      <thead>
        <tr className="border-b border-border text-xs text-muted">
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Task
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Target
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Status
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Stage
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Started
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Duration
          </th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((task) => (
          <tr
            key={task.id}
            tabIndex={0}
            role="button"
            aria-label={`View details for ${task.id}`}
            onClick={() => onSelect(task)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSelect(task);
            }}
            className="motion-safe-transition cursor-pointer border-b border-border/60 hover:bg-surface-raised/40"
          >
            <td className="py-3 pr-4">
              <p className="font-mono text-xs text-muted">{task.id}</p>
              <p className="max-w-xs truncate text-foreground">{task.objective}</p>
            </td>
            <td className="py-3 pr-4 text-muted-strong">{task.targetName}</td>
            <td className="py-3 pr-4">
              <TaskStatusBadge status={task.status} />
            </td>
            <td className="py-3 pr-4 text-muted-strong">{titleCase(task.stage)}</td>
            <td className="py-3 pr-4 text-muted-strong">{formatRelativeDate(task.startedAt)}</td>
            <td className="py-3 pr-4 text-muted-strong">{formatDuration(task.durationSeconds)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
