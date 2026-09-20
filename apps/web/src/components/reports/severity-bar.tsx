import type { Severity, SeveritySummary } from "@/types/dashboard";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "bg-danger",
  high: "bg-warning",
  medium: "bg-warning/60",
  low: "bg-info/60",
  info: "bg-muted",
};

export function SeverityBar({ summary }: { summary: SeveritySummary }) {
  const total = Object.values(summary).reduce((sum, count) => sum + count, 0);
  if (total === 0) {
    return <p className="text-xs text-muted">No findings.</p>;
  }

  return (
    <div className="space-y-1.5">
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
        {SEVERITY_ORDER.map((severity) => {
          const count = summary[severity];
          if (count === 0) return null;
          return (
            <div
              key={severity}
              className={SEVERITY_COLOR[severity]}
              style={{ width: `${(count / total) * 100}%` }}
              title={`${severity}: ${count}`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-muted">
        {SEVERITY_ORDER.filter((severity) => summary[severity] > 0).map((severity) => (
          <span key={severity} className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_COLOR[severity]}`} aria-hidden="true" />
            {severity} ({summary[severity]})
          </span>
        ))}
      </div>
    </div>
  );
}
