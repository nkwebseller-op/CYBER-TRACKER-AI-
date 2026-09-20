import { Card } from "@/components/ui/card";

export default function ToolDiscoveryPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Tool Discovery</h1>
        <p className="text-sm text-muted">
          Tool Intelligence: compatibility, provenance, and install specs for vetted security
          tools. The registry (services/tools/registry.py) is intentionally empty in Phase 1.
        </p>
      </div>
      <Card>
        <p className="text-sm text-muted">No tools registered yet.</p>
      </Card>
    </div>
  );
}
