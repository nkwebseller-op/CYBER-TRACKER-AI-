import {
  LayoutDashboard,
  MessageSquare,
  Settings,
  SquareTerminal,
  Target,
  Wrench,
  ClipboardList,
  FileText,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  description: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", description: "System status & overview", icon: LayoutDashboard },
  { label: "Chat", href: "/chat", description: "AI command center", icon: MessageSquare },
  { label: "Targets", href: "/targets", description: "Authorized scope", icon: Target },
  { label: "Tasks", href: "/tasks", description: "Planned & running work", icon: ClipboardList },
  { label: "Tool Discovery", href: "/tool-discovery", description: "Tool intelligence", icon: Wrench },
  { label: "Terminal", href: "/terminal", description: "Live execution output", icon: SquareTerminal },
  { label: "Reports", href: "/reports", description: "Findings & reports", icon: FileText },
  { label: "Settings", href: "/settings", description: "Providers & policy", icon: Settings },
];
