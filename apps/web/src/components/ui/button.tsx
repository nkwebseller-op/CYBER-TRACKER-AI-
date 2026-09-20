import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-contrast hover:bg-accent/90",
  secondary:
    "bg-surface-raised text-foreground border border-border-strong hover:bg-surface-hover",
  ghost: "bg-transparent text-muted-strong hover:bg-surface-raised hover:text-foreground",
  danger: "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
};

const SIZE_STYLES: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`motion-safe-transition inline-flex items-center justify-center gap-2 rounded-md font-medium disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]} ${className}`}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}
