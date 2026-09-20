import { Card } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/api";

interface Target {
  id: string;
  name: string;
  scope_type: string;
  scope_value: string;
  authorized_by: string;
  is_active: boolean;
}

async function fetchTargets(): Promise<Target[] | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/targets`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export default async function TargetsPage() {
  const targets = await fetchTargets();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Targets</h1>
        <p className="text-sm text-muted">
          Authorized scope entries. Nothing may be executed against a target without an active,
          non-expired record here — enforced by the Policy Engine, not the UI.
        </p>
      </div>

      {targets === null && (
        <Card>
          <p className="text-sm text-warning">
            Could not reach the API at {API_BASE_URL}. Start the backend to manage targets.
          </p>
        </Card>
      )}

      {targets !== null && targets.length === 0 && (
        <Card>
          <p className="text-sm text-muted">No authorized targets yet.</p>
        </Card>
      )}

      {targets && targets.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {targets.map((target) => (
            <Card key={target.id} title={target.name} subtitle={target.scope_type}>
              <p className="truncate text-sm text-foreground">{target.scope_value}</p>
              <p className="mt-1 text-xs text-muted">Authorized by {target.authorized_by}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
