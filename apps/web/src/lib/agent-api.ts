/**
 * Thin client for the Phase 12 Agent Orchestrator API
 * (apps/api/app/api/routes/agent.py). No method here sends a command or
 * argv — only objective/target declarations and explicit step/approve/
 * reject/pause/resume/cancel/clarify actions on an existing task.
 */

import { API_BASE_URL } from "@/lib/api";
import type { AgentEvent, AgentTask } from "@/types/agent";

async function parseOrThrow<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body?.detail?.message ?? body?.detail ?? `${action} failed (${response.status})`;
    throw new Error(message);
  }
  return response.json();
}

export async function createAgentTask(input: {
  objective: string;
  userRequest: string;
  target?: string;
  targetId?: string;
  authorizationStatus?: string;
}): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseOrThrow(response, "Create agent task");
}

export async function getAgentTask(taskId: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}`);
  return parseOrThrow(response, "Get agent task");
}

export async function stepAgentTask(
  taskId: string,
  options: { targetId?: string; platform?: string } = {}
): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  return parseOrThrow(response, "Advance agent task");
}

export async function pauseAgentTask(taskId: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/pause`, {
    method: "POST",
  });
  return parseOrThrow(response, "Pause agent task");
}

export async function resumeAgentTask(taskId: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/resume`, {
    method: "POST",
  });
  return parseOrThrow(response, "Resume agent task");
}

export async function cancelAgentTask(taskId: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/cancel`, {
    method: "POST",
  });
  return parseOrThrow(response, "Cancel agent task");
}

export async function approveAgentAction(taskId: string, approvedBy: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approvedBy }),
  });
  return parseOrThrow(response, "Approve agent action");
}

export async function rejectAgentAction(taskId: string, reason: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  return parseOrThrow(response, "Reject agent action");
}

export async function clarifyAgentTask(taskId: string, answer: string): Promise<AgentTask> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  return parseOrThrow(response, "Provide clarification");
}

export async function getAgentTaskEvents(taskId: string): Promise<AgentEvent[]> {
  const response = await fetch(`${API_BASE_URL}/api/agent/tasks/${taskId}/events`);
  return parseOrThrow(response, "Get agent task events");
}
