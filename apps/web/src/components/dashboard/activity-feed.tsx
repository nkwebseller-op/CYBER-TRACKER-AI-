import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ActivityEvent, ActivityStatus } from "@/types/dashboard";

const STATUS_ICON = {
  success: CheckCircle2,
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
} satisfies Record<ActivityStatus, unknown>;

const STATUS_COLOR: Record<ActivityStatus, string> = {
  success: "text-accent",
  info: "text-info",
  warning: "text-warning",
  error: "text-danger",
};

export function ActivityFeed({
  events,
  compact = false,
}: {
  events: ActivityEvent[];
  compact?: boolean;
}) {
  return (
    <ol className="space-y-3">
      {events.map((event) => {
        const Icon = STATUS_ICON[event.status];
        return (
          <li key={event.id} className="flex gap-3">
            <Icon
              size={16}
              className={`mt-0.5 flex-shrink-0 ${STATUS_COLOR[event.status]}`}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-medium text-foreground">{event.type}</p>
                <time className="flex-shrink-0 text-xs text-muted">{event.timestamp}</time>
              </div>
              {!compact && <p className="mt-0.5 text-xs text-muted">{event.description}</p>}
              {compact && (
                <p className="mt-0.5 truncate text-xs text-muted">{event.description}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
