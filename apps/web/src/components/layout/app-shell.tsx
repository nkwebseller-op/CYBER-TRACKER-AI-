"use client";

import { useState, type ReactNode } from "react";
import { ActivityPanel } from "@/components/layout/activity-panel";
import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";

export function AppShell({ children }: { children: ReactNode }) {
  const [isMobileNavOpen, setMobileNavOpen] = useState(false);
  const [isActivityOpen, setActivityOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-contrast"
      >
        Skip to main content
      </a>

      <div className="glass hidden w-64 flex-shrink-0 border-r border-border md:block">
        <Sidebar />
      </div>

      <MobileNav isOpen={isMobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileNavOpen(true)}
          onActivityClick={() => setActivityOpen((open) => !open)}
          isActivityOpen={isActivityOpen}
        />
        <div className="flex flex-1 overflow-hidden">
          <main
            id="main-content"
            tabIndex={-1}
            className="flex-1 overflow-y-auto p-4 sm:p-6"
          >
            {children}
          </main>
          {isActivityOpen && <ActivityPanel />}
        </div>
      </div>
    </div>
  );
}
