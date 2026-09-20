"use client";

import { Search, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import { ToolCard } from "@/components/tools/tool-card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import type { DiscoveredTool } from "@/types/dashboard";

const CATEGORY_ALL = "All Categories";

export function ToolsView({ tools }: { tools: DiscoveredTool[] }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState(CATEGORY_ALL);

  const categories = useMemo(
    () => [CATEGORY_ALL, ...Array.from(new Set(tools.map((tool) => tool.category)))],
    [tools]
  );

  const filtered = useMemo(() => {
    return tools.filter((tool) => {
      const matchesCategory = category === CATEGORY_ALL || tool.category === category;
      const matchesQuery =
        query.trim().length === 0 ||
        tool.name.toLowerCase().includes(query.toLowerCase()) ||
        tool.description.toLowerCase().includes(query.toLowerCase());
      return matchesCategory && matchesQuery;
    });
  }, [tools, query, category]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tool Discovery"
        description="Tool Intelligence: compatibility, provenance, and install specs for vetted security tools. Nothing here is installed or executed automatically."
      />

      <Panel>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search tools…"
              aria-label="Search tools"
              className="pl-9"
            />
          </div>
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            aria-label="Filter by category"
            className="motion-safe-transition rounded-md border border-border-strong bg-surface-raised px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title="No tools match your search"
            description="Try a different keyword or category filter."
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((tool) => (
              <ToolCard key={tool.id} tool={tool} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
