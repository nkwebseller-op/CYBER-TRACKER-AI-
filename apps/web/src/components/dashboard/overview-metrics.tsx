import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import type { OverviewMetric } from "@/types/dashboard";

const TREND_ICON = { up: ArrowUp, down: ArrowDown, flat: ArrowRight } as const;
const TREND_COLOR = { up: "text-accent", down: "text-muted", flat: "text-muted" } as const;

export function OverviewMetrics({ metrics }: { metrics: OverviewMetric[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {metrics.map((metric) => {
        const TrendIcon = metric.trend ? TREND_ICON[metric.trend] : null;
        return (
          <div
            key={metric.id}
            className="glass motion-safe-transition rounded-lg p-4 hover:border-border-strong"
          >
            <p className="text-xs text-muted">{metric.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
              {metric.value}
            </p>
            {metric.delta && (
              <p
                className={`mt-1.5 flex items-center gap-1 text-xs ${
                  metric.trend ? TREND_COLOR[metric.trend] : "text-muted"
                }`}
              >
                {TrendIcon && <TrendIcon size={11} aria-hidden="true" />}
                {metric.delta}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
