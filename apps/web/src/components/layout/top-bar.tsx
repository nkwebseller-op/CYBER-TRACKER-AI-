"use client";

import { Activity, Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";
import { StatusPill } from "@/components/ui/status-pill";

export function TopBar({
  onMenuClick,
  onActivityClick,
  isActivityOpen,
}: {
  onMenuClick: () => void;
  onActivityClick: () => void;
  isActivityOpen: boolean;
}) {
  const pathname = usePathname();
  const current = NAV_ITEMS.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );

  return (
    <header className="glass flex h-14 flex-shrink-0 items-center justify-between gap-3 border-b border-border px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="motion-safe-transition rounded-md p-1.5 text-muted hover:bg-surface-raised hover:text-foreground md:hidden"
        >
          <Menu size={19} />
        </button>
        <div>
          <p className="text-sm font-medium text-foreground">{current?.label ?? "Cyber AI"}</p>
          <p className="hidden text-xs text-muted sm:block">{current?.description}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-2 lg:flex">
          <StatusPill label="API" state="unknown" />
          <StatusPill label="AI Provider" state="unknown" />
          <StatusPill label="Database" state="unknown" />
        </div>
        <button
          onClick={onActivityClick}
          aria-label="Toggle activity panel"
          aria-pressed={isActivityOpen}
          className={`motion-safe-transition hidden rounded-md p-1.5 lg:flex ${
            isActivityOpen
              ? "bg-surface-raised text-accent"
              : "text-muted hover:bg-surface-raised hover:text-foreground"
          }`}
        >
          <Activity size={18} />
        </button>
      </div>
    </header>
  );
}
