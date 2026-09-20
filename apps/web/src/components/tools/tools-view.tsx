"use client";

import { Search, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import { ToolCard } from "@/components/tools/tool-card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { titleCase } from "@/lib/format";
import type { RegistryTool, TrustStatus } from "@/types/tools";

const CATEGORY_ALL = "All Categories";
const TRUST_ALL = "All Trust States";

/**
 * Real Trusted Tool Registry data, backed by the Phase 10 API
 * (apps/api/app/api/routes/tools.py). Search/category/trust filtering is
 * client-side over the already-fetched list. Nothing in this view
 * installs or executes a tool — see the tool card for provenance/risk
 * badges instead of an action button.
 */
export function ToolsView({
  tools,
  isLoading = false,
  error = null,
}: {
  tools: RegistryTool[];
  isLoading?: boolean;
  error?: string | null;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState(CATEGORY_ALL);
  const [trustStatus, setTrustStatus] = useState(TRUST_ALL);

  const categories = useMemo(
    () => [CATEGORY_ALL, ...Array.from(new Set(tools.map((tool) => tool.category)))],
    [tools]
  );
  const trustStates = useMemo(
    () => [TRUST_ALL, ...Array.from(new Set(tools.map((tool) => tool.trustStatus)))],
    [tools]
  );

  const filtered = useMemo(() => {
    return tools.filter((tool) => {
      const matchesCategory = category === CATEGORY_ALL || tool.category === category;
      const matchesTrust = trustStatus === TRUST_ALL || tool.trustStatus === trustStatus;
      const needle = query.trim().toLowerCase();
      const matchesQuery =
        needle.length === 0 ||
        tool.name.toLowerCase().includes(needle) ||
        tool.displayName.toLowerCase().includes(needle) ||
        tool.description.toLowerCase().includes(needle) ||
        tool.capabilities.some((c) => c.toLowerCase().includes(needle));
      return matchesCategory && matchesTrust && matchesQuery;
    });
  }, [tools, query, category, trustStatus]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tool Discovery"
        description="Trusted Tool Registry: provenance, verification status, and platform compatibility for candidate security tools. Nothing here is installed or executed automatically."
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
              placeholder="Search tools or capabilities…"
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
                {item === CATEGORY_ALL ? item : titleCase(item)}
              </option>
            ))}
          </select>
          <select
            value={trustStatus}
            onChange={(event) => setTrustStatus(event.target.value as TrustStatus | string)}
            aria-label="Filter by trust status"
            className="motion-safe-transition rounded-md border border-border-strong bg-surface-raised px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
          >
            {trustStates.map((item) => (
              <option key={item} value={item}>
                {item === TRUST_ALL ? item : titleCase(item)}
              </option>
            ))}
          </select>
        </div>

        {error ? (
          <EmptyState
            icon={Wrench}
            title="Could not reach the Tool Registry API"
            description={error}
          />
        ) : isLoading ? (
          <EmptyState icon={Wrench} title="Loading tools…" description="" />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title="No tools match your search"
            description="Try a different keyword, category, or trust filter."
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
