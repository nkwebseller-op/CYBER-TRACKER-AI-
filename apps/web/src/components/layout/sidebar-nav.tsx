"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={`motion-safe-transition group relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm ${
              isActive
                ? "bg-surface-raised text-foreground"
                : "text-muted hover:bg-surface-raised/60 hover:text-foreground"
            }`}
          >
            <span
              className={`absolute left-0 top-1/2 h-5 -translate-y-1/2 rounded-full bg-accent motion-safe-transition ${
                isActive ? "w-0.5 opacity-100" : "w-0.5 opacity-0"
              }`}
              aria-hidden="true"
            />
            <Icon
              size={17}
              className={isActive ? "text-accent" : "text-muted group-hover:text-muted-strong"}
              aria-hidden="true"
            />
            <span className="flex flex-col">
              <span className={`font-medium ${isActive ? "text-foreground" : ""}`}>
                {item.label}
              </span>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
