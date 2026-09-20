import type { ReactNode } from "react";

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
  raised = false,
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  raised?: boolean;
}) {
  return (
    <section className={`${raised ? "glass-raised" : "glass"} rounded-lg ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div>
            {title && <h2 className="text-sm font-semibold text-foreground">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
