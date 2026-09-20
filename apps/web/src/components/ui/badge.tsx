import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "info" | "warning" | "danger";

const TONE_STYLES: Record<BadgeTone, string> = {
  neutral: "bg-surface-raised text-muted-strong border-border-strong",
  accent: "bg-accent-soft/20 text-accent border-accent-soft/40",
  info: "bg-info-soft text-info border-info/30",
  warning: "bg-warning-soft text-warning border-warning/30",
  danger: "bg-danger-soft text-danger border-danger/30",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE_STYLES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
