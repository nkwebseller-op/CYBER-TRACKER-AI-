import { StatusPill } from "@/components/ui/status-pill";

export function TopBar() {
  return (
    <header className="glass flex h-14 flex-shrink-0 items-center justify-between border-b border-border px-6">
      <div className="text-sm text-muted">
        Authorized cybersecurity operations —{" "}
        <span className="text-foreground">no live executions in this phase</span>
      </div>
      <div className="flex items-center gap-3">
        <StatusPill label="API" state="unknown" />
        <StatusPill label="AI Provider" state="unknown" />
        <StatusPill label="Database" state="unknown" />
      </div>
    </header>
  );
}
