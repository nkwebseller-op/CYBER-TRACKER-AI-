import { Card } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted">
          System overview. Phase 1: no live executions or findings exist yet — the pipeline
          shown below is wired at the architecture level, not yet driven by real data.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="Active Targets" subtitle="Authorized scope">
          <p className="text-2xl font-semibold text-accent">0</p>
        </Card>
        <Card title="Running Tasks" subtitle="In progress">
          <p className="text-2xl font-semibold text-accent">0</p>
        </Card>
        <Card title="Pending Approvals" subtitle="Policy gate">
          <p className="text-2xl font-semibold text-warning">0</p>
        </Card>
        <Card title="Findings" subtitle="All reports">
          <p className="text-2xl font-semibold text-accent">0</p>
        </Card>
      </div>

      <Card title="Pipeline" subtitle="AI intent → policy → execution → report">
        <ol className="grid grid-cols-2 gap-3 text-xs text-muted sm:grid-cols-4">
          {[
            "AI Orchestrator",
            "Task Planner",
            "Research Engine",
            "Tool Intelligence",
            "Policy Engine",
            "Execution Controller",
            "Result Analyzer",
            "Report Engine",
          ].map((stage, index) => (
            <li
              key={stage}
              className="rounded-md border border-border bg-surface-raised px-3 py-2 text-foreground"
            >
              <span className="mr-1 font-mono text-accent">{index + 1}.</span>
              {stage}
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
