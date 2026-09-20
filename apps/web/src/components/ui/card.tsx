import type { ReactNode } from "react";

export function Card({
  title,
  subtitle,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`glass rounded-lg p-5 ${className}`}>
      {title && (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
