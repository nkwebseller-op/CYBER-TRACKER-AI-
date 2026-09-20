import { Badge } from "@/components/ui/badge";
import { TOOL_INSTALL_TONE, TOOL_PROVENANCE_TONE } from "@/lib/status-styles";
import { titleCase } from "@/lib/format";
import type { DiscoveredTool } from "@/types/dashboard";

export function ToolCard({ tool }: { tool: DiscoveredTool }) {
  return (
    <div className="motion-safe-transition flex flex-col gap-3 rounded-md border border-border bg-surface-raised/50 p-4 hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-foreground">{tool.name}</p>
          <p className="text-xs text-muted">{tool.category}</p>
        </div>
        <Badge tone={TOOL_INSTALL_TONE[tool.installStatus]}>{titleCase(tool.installStatus)}</Badge>
      </div>

      <p className="text-xs text-muted">{tool.description}</p>

      <div className="flex flex-wrap items-center gap-1.5">
        {tool.platforms.map((platform) => (
          <Badge key={platform} tone="neutral">
            {platform}
          </Badge>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted">
          {tool.source} · v{tool.version}
        </span>
        <Badge tone={TOOL_PROVENANCE_TONE[tool.provenance]}>{titleCase(tool.provenance)}</Badge>
      </div>
    </div>
  );
}
