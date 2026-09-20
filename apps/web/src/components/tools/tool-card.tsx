import { Badge } from "@/components/ui/badge";
import { RISK_LEVEL_TONE, TRUST_STATUS_TONE } from "@/lib/status-styles";
import { titleCase } from "@/lib/format";
import type { RegistryTool } from "@/types/tools";

export function ToolCard({ tool }: { tool: RegistryTool }) {
  return (
    <div className="motion-safe-transition flex flex-col gap-3 rounded-md border border-border bg-surface-raised/50 p-4 hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-foreground">{tool.displayName}</p>
          <p className="text-xs text-muted">{titleCase(tool.category)}</p>
        </div>
        <Badge tone={TRUST_STATUS_TONE[tool.trustStatus]}>{titleCase(tool.trustStatus)}</Badge>
      </div>

      <p className="text-xs text-muted">{tool.description}</p>

      <div className="flex flex-wrap items-center gap-1.5">
        {tool.supportedPlatforms.map((platform) => (
          <Badge key={platform} tone="neutral">
            {platform}
          </Badge>
        ))}
      </div>

      {tool.capabilities.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          {tool.capabilities.map((capability) => (
            <span
              key={capability}
              className="rounded-sm border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted"
            >
              {capability.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted">
          {tool.provenance.publisher ?? titleCase(tool.provenance.sourceType)}
          {tool.version ? ` · v${tool.version}` : ""}
        </span>
        <Badge tone={RISK_LEVEL_TONE[tool.riskLevel]}>{titleCase(tool.riskLevel)} risk</Badge>
      </div>
    </div>
  );
}
