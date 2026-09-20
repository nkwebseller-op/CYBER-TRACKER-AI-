import { Badge } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { AGENT_STATE_TONE } from "@/lib/status-styles";
import type { AgentStatusEntry } from "@/types/dashboard";

const PULSING_STATES = new Set(["ONLINE", "RUNNING"]);

export function AgentStatusGrid({ agents }: { agents: AgentStatusEntry[] }) {
  return (
    <Panel title="Agent Status" subtitle="Subsystem health across the pipeline">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="rounded-md border border-border bg-surface-raised/60 p-3.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-foreground">{agent.name}</p>
                <p className="text-xs text-muted">{agent.description}</p>
              </div>
              <Badge tone={AGENT_STATE_TONE[agent.state]} className="shrink-0">
                <span
                  className={`h-1.5 w-1.5 rounded-full bg-current ${
                    PULSING_STATES.has(agent.state) ? "animate-pulse-dot" : ""
                  }`}
                  aria-hidden="true"
                />
                {agent.state}
              </Badge>
            </div>
            {agent.detail && <p className="mt-2 text-xs text-muted">{agent.detail}</p>}
          </div>
        ))}
      </div>
    </Panel>
  );
}
