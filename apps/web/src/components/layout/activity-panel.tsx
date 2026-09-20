import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { MOCK_RECENT_ACTIVITY } from "@/lib/mock";

export function ActivityPanel() {
  return (
    <aside className="glass hidden w-80 flex-shrink-0 flex-col overflow-y-auto border-l border-border p-4 lg:flex">
      <h2 className="mb-3 text-sm font-semibold text-foreground">Live Activity</h2>
      <p className="mb-4 text-xs text-muted">
        Mock event stream — will subscribe to the WebSocket gateway once real executions exist.
      </p>
      <ActivityFeed events={MOCK_RECENT_ACTIVITY} compact />
    </aside>
  );
}
