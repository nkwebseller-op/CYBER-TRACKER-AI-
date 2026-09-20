import { Eye } from "lucide-react";
import { SeverityBar } from "@/components/reports/severity-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { REPORT_STATUS_TONE } from "@/lib/status-styles";
import { formatRelativeDate, titleCase } from "@/lib/format";
import type { SecurityReport } from "@/types/dashboard";

export function ReportCard({ report }: { report: SecurityReport }) {
  return (
    <div className="motion-safe-transition rounded-md border border-border bg-surface-raised/50 p-4 hover:border-border-strong">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium text-foreground">{report.title}</p>
            <Badge tone={REPORT_STATUS_TONE[report.status]}>{titleCase(report.status)}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted">
            {report.targetName} · {formatRelativeDate(report.assessedAt)} · {report.findingsCount}{" "}
            findings
          </p>
          <div className="mt-3 max-w-md">
            <SeverityBar summary={report.severitySummary} />
          </div>
        </div>
        <Button size="sm" variant="secondary" icon={<Eye size={13} />}>
          View report
        </Button>
      </div>
    </div>
  );
}
