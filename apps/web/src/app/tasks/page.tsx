import { Card } from "@/components/ui/card";

export default function TasksPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Tasks</h1>
        <p className="text-sm text-muted">
          Planned and running units of work produced by the Task Planner. No tasks exist yet —
          this phase does not wire the AI Orchestrator to task creation.
        </p>
      </div>
      <Card>
        <p className="text-sm text-muted">No tasks yet.</p>
      </Card>
    </div>
  );
}
