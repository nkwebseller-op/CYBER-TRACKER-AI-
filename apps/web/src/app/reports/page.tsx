import { FileText } from "lucide-react";
import { ReportCard } from "@/components/reports/report-card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { MOCK_REPORTS } from "@/lib/mock";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Findings produced by the Result Analyzer and rendered by the Report Engine."
      />

      <Panel>
        {MOCK_REPORTS.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports yet"
            description="Reports appear here once a task completes analysis."
          />
        ) : (
          <div className="space-y-3">
            {MOCK_REPORTS.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
