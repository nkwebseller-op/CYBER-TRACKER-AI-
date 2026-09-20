import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode } from "react";

export function Input({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`motion-safe-transition w-full rounded-md border border-border-strong bg-surface-raised px-3 py-2 text-sm text-foreground placeholder:text-muted outline-none focus:border-accent ${className}`}
      {...rest}
    />
  );
}

export function Field({
  label,
  hint,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  htmlFor?: string;
} & LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-xs font-medium text-muted-strong">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}
