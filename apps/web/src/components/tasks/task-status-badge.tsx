import { Badge } from "@/components/ui/badge";
import { TASK_STATUS_TONE } from "@/lib/status-styles";
import { titleCase } from "@/lib/format";
import type { TaskStatus } from "@/types/dashboard";

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <Badge tone={TASK_STATUS_TONE[status]}>{titleCase(status)}</Badge>;
}
