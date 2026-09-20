"use client";

import { useState } from "react";

export interface TabItem {
  id: string;
  label: string;
}

export function Tabs({
  tabs,
  defaultTabId,
  onChange,
}: {
  tabs: TabItem[];
  defaultTabId?: string;
  onChange?: (tabId: string) => void;
}) {
  const [activeId, setActiveId] = useState(defaultTabId ?? tabs[0]?.id);

  function selectTab(id: string) {
    setActiveId(id);
    onChange?.(id);
  }

  return (
    <div role="tablist" aria-label="Sections" className="flex gap-1 border-b border-border">
      {tabs.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => selectTab(tab.id)}
            className={`motion-safe-transition relative px-3 py-2.5 text-sm font-medium ${
              isActive ? "text-accent" : "text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
            {isActive && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-accent" />
            )}
          </button>
        );
      })}
    </div>
  );
}
