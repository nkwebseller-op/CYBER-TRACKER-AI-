import { AgentStatusGrid } from "@/components/dashboard/agent-status-grid";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { OverviewMetrics } from "@/components/dashboard/overview-metrics";
import { WorkflowPipeline } from "@/components/dashboard/workflow-pipeline";
import { TerminalLines } from "@/components/terminal/terminal-lines";
import { Panel } from "@/components/ui/panel";
import { PageHeader } from "@/components/ui/page-header";
import {
  MOCK_AGENT_STATUS,
  MOCK_OVERVIEW_METRICS,
  MOCK_RECENT_ACTIVITY,
  MOCK_TERMINAL_PREVIEW,
  MOCK_WORKFLOW_STAGES,
} from "@/lib/mock";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="System overview across the authorization → execution pipeline. All data below is mock — no live executions exist in this phase."
      />

      <OverviewMetrics metrics={MOCK_OVERVIEW_METRICS} />

      <WorkflowPipeline stages={MOCK_WORKFLOW_STAGES} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <AgentStatusGrid agents={MOCK_AGENT_STATUS} />
        </div>
        <Panel title="Recent Activity" subtitle="Latest pipeline events">
          <ActivityFeed events={MOCK_RECENT_ACTIVITY} />
        </Panel>
      </div>

      <Panel title="Terminal Activity Preview" subtitle="Read-only preview — no commands are executed in this phase">
        <TerminalLines lines={MOCK_TERMINAL_PREVIEW} />
      </Panel>
    </div>
  );
}
