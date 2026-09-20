export interface NavItem {
  label: string;
  href: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", description: "System status & overview" },
  { label: "Chat", href: "/chat", description: "AI command center" },
  { label: "Targets", href: "/targets", description: "Authorized scope" },
  { label: "Tasks", href: "/tasks", description: "Planned & running work" },
  { label: "Tool Discovery", href: "/tool-discovery", description: "Tool intelligence" },
  { label: "Terminal", href: "/terminal", description: "Live execution output" },
  { label: "Reports", href: "/reports", description: "Findings & reports" },
  { label: "Settings", href: "/settings", description: "Providers & policy" },
];
