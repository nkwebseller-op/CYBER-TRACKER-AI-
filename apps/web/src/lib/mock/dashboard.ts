import type {
  ActivityEvent,
  AgentStatusEntry,
  OverviewMetric,
  TerminalLine,
  WorkflowStage,
} from "@/types/dashboard";

export const MOCK_OVERVIEW_METRICS: OverviewMetric[] = [
  { id: "active-tasks", label: "Active Tasks", value: 3, delta: "+1 today", trend: "up" },
  { id: "authorized-targets", label: "Authorized Targets", value: 8, delta: "+2 this week", trend: "up" },
  { id: "available-tools", label: "Available Tools", value: 14, delta: "no change", trend: "flat" },
  { id: "findings", label: "Findings", value: 27, delta: "-4 resolved", trend: "down" },
  { id: "running-agents", label: "Running Agents", value: 2, delta: "steady", trend: "flat" },
];

export const MOCK_AGENT_STATUS: AgentStatusEntry[] = [
  {
    id: "ai-agent",
    name: "AI Agent",
    description: "Orchestrator + Task Planner",
    state: "ONLINE",
    detail: "Gemini 2.5 Flash",
  },
  {
    id: "terminal-engine",
    name: "Terminal Engine",
    description: "Execution Controller",
    state: "READY",
    detail: "Linux adapter selected",
  },
  {
    id: "research-engine",
    name: "Research Engine",
    description: "Tool & technique discovery",
    state: "IDLE",
    detail: "No active queries",
  },
  {
    id: "tool-engine",
    name: "Tool Engine",
    description: "Tool Intelligence registry",
    state: "RUNNING",
    detail: "Refreshing provenance data",
  },
  {
    id: "policy-engine",
    name: "Policy Engine",
    description: "Authorization & risk gating",
    state: "ONLINE",
    detail: "0 pending approvals",
  },
  {
    id: "database",
    name: "Database",
    description: "PostgreSQL",
    state: "WARNING",
    detail: "Connection pool near capacity",
  },
];

export const MOCK_WORKFLOW_STAGES: WorkflowStage[] = [
  { key: "UNDERSTAND", label: "Understand", status: "complete" },
  { key: "RESEARCH", label: "Research", status: "complete" },
  { key: "SELECT", label: "Select", status: "complete" },
  { key: "APPROVE", label: "Approve", status: "active" },
  { key: "PREPARE", label: "Prepare", status: "pending" },
  { key: "RUN", label: "Run", status: "pending" },
  { key: "ANALYZE", label: "Analyze", status: "pending" },
  { key: "REPORT", label: "Report", status: "pending" },
];

export const MOCK_RECENT_ACTIVITY: ActivityEvent[] = [
  {
    id: "evt-1",
    timestamp: "2m ago",
    type: "Objective Received",
    description: "\"Assess the security of my authorized web server.\"",
    status: "info",
  },
  {
    id: "evt-2",
    timestamp: "2m ago",
    type: "Scope Validated",
    description: "Target api.staging.internal matched an active authorization record.",
    status: "success",
  },
  {
    id: "evt-3",
    timestamp: "1m ago",
    type: "Tool Discovered",
    description: "3 candidate tools found for domain: web application security.",
    status: "info",
  },
  {
    id: "evt-4",
    timestamp: "1m ago",
    type: "Tool Selected",
    description: "HTTP header analyzer selected (low risk, in-scope).",
    status: "success",
  },
  {
    id: "evt-5",
    timestamp: "45s ago",
    type: "Task Approval Requested",
    description: "Directory enumeration flagged medium risk — awaiting approval.",
    status: "warning",
  },
  {
    id: "evt-6",
    timestamp: "12s ago",
    type: "Terminal Command Prepared",
    description: "Command staged on linux adapter, not yet executed.",
    status: "info",
  },
  {
    id: "evt-7",
    timestamp: "just now",
    type: "Analysis Completed",
    description: "Header scan finished with 2 informational findings.",
    status: "success",
  },
];

export const MOCK_TERMINAL_PREVIEW: TerminalLine[] = [
  { id: "l1", kind: "system", text: "session: linux · adapter: LocalProcessAdapter", timestamp: "04:12:01" },
  { id: "l2", kind: "command", text: "$ curl -sI https://api.staging.internal", timestamp: "04:12:03" },
  { id: "l3", kind: "stdout", text: "HTTP/2 200", timestamp: "04:12:03" },
  { id: "l4", kind: "stdout", text: "server: nginx/1.25.3", timestamp: "04:12:03" },
  { id: "l5", kind: "stdout", text: "strict-transport-security: missing", timestamp: "04:12:03" },
  { id: "l6", kind: "system", text: "awaiting approval for next action…", timestamp: "04:12:04" },
];
