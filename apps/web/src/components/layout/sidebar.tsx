import Link from "next/link";
import { NAV_ITEMS } from "@/lib/nav";

export function Sidebar() {
  return (
    <aside className="glass flex w-64 flex-shrink-0 flex-col border-r border-border">
      <div className="flex items-center gap-2 border-b border-border px-5 py-5">
        <div className="h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_10px_var(--accent)]" />
        <span className="glow-text font-mono text-sm font-semibold tracking-wide text-accent">
          CYBER AI SYSTEM
        </span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="group flex flex-col gap-0.5 rounded-md px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-raised hover:text-foreground"
          >
            <span className="font-medium text-foreground/90 group-hover:text-accent">
              {item.label}
            </span>
            <span className="text-xs text-muted">{item.description}</span>
          </Link>
        ))}
      </nav>
      <div className="border-t border-border px-5 py-4 text-xs text-muted">
        Phase 1 — Foundation
      </div>
    </aside>
  );
}
