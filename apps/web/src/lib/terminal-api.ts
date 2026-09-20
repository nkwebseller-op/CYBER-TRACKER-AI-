/**
 * Thin client for the Phase 5 Terminal Engine API
 * (apps/api/app/api/routes/terminal.py). There is no endpoint here that
 * accepts raw command text — sessions and status only. Executing a
 * reviewed action still requires a real target and passes through the
 * Policy Engine server-side; this client intentionally has no
 * "run this shell command" method.
 */

import { API_BASE_URL } from "@/lib/api";

export type TerminalSessionStatus =
  | "CREATED"
  | "READY"
  | "RUNNING"
  | "STOPPING"
  | "STOPPED"
  | "FAILED"
  | "EXPIRED";

export type TerminalPlatform = "WINDOWS" | "LINUX" | "MACOS" | "ANDROID_TERMUX" | "UNKNOWN";

export interface TerminalSessionInfo {
  id: string;
  platform: TerminalPlatform;
  status: TerminalSessionStatus;
  createdAt: string;
  lastActivityAt: string;
  workingDirectory: string | null;
  taskId: string | null;
}

export async function createTerminalSession(taskId?: string): Promise<TerminalSessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/terminal/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(taskId ? { taskId } : {}),
  });
  if (!response.ok) {
    throw new Error(`Failed to create terminal session (${response.status})`);
  }
  return response.json();
}

export async function getTerminalSession(sessionId: string): Promise<TerminalSessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/terminal/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch terminal session (${response.status})`);
  }
  return response.json();
}
