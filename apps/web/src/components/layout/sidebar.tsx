import { SidebarNav } from "@/components/layout/sidebar-nav";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 border-b border-border px-5 py-5">
        <div
          className="h-2 w-2 rounded-full bg-accent animate-pulse-dot"
          aria-hidden="true"
        />
        <span className="glow-text font-mono text-sm font-semibold tracking-wide text-accent">
          CYBER AI SYSTEM
        </span>
      </div>
      <SidebarNav onNavigate={onNavigate} />
      <div className="border-t border-border px-5 py-4 text-xs text-muted">
        Phase 2 — Dashboard UI
      </div>
    </div>
  );
}
