export type StatusState = "ok" | "degraded" | "down" | "unknown";

const STATE_STYLES: Record<StatusState, string> = {
  ok: "bg-accent",
  degraded: "bg-warning",
  down: "bg-danger",
  unknown: "bg-muted",
};

export function StatusPill({ label, state }: { label: string; state: StatusState }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-surface-raised px-3 py-1 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${STATE_STYLES[state]}`} />
      <span className="text-muted">{label}</span>
    </div>
  );
}
