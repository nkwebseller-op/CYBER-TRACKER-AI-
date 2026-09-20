import { Card } from "@/components/ui/card";

export default function ReportsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Reports</h1>
        <p className="text-sm text-muted">
          Findings produced by the Result Analyzer and rendered by the Report Engine.
        </p>
      </div>
      <Card>
        <p className="text-sm text-muted">No reports generated yet.</p>
      </Card>
    </div>
  );
}
