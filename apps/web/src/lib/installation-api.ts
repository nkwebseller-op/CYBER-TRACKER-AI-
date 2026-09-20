/**
 * Thin client for the Phase 11 Tool Installation API
 * (apps/api/app/api/routes/installation.py). No method here sends raw
 * argv or a shell string — only toolId/targetId/platform and explicit
 * approve/reject/start/cancel actions on an already-created request.
 */

import { API_BASE_URL } from "@/lib/api";
import type { InstallationRequest, ReadinessReport } from "@/types/installation";

async function parseOrThrow<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body?.detail?.message ?? body?.detail ?? `${action} failed (${response.status})`;
    throw new Error(message);
  }
  return response.json();
}

export async function checkReadiness(
  toolId: string,
  targetId: string,
  platform: string
): Promise<ReadinessReport> {
  const query = new URLSearchParams({ tool_id: toolId, target_id: targetId, platform });
  const response = await fetch(`${API_BASE_URL}/api/installations/readiness?${query.toString()}`);
  return parseOrThrow(response, "Readiness check");
}

export async function requestInstallation(
  toolId: string,
  targetId: string,
  platform: string
): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ toolId, targetId, platform }),
  });
  return parseOrThrow(response, "Installation request");
}

export async function approveInstallation(
  requestId: string,
  approvedBy: string
): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations/${requestId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approvedBy }),
  });
  return parseOrThrow(response, "Approval");
}

export async function rejectInstallation(
  requestId: string,
  reason: string
): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations/${requestId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  return parseOrThrow(response, "Rejection");
}

export async function startInstallation(
  requestId: string,
  targetId: string
): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations/${requestId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ targetId }),
  });
  return parseOrThrow(response, "Installation");
}

export async function cancelInstallation(requestId: string): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations/${requestId}/cancel`, {
    method: "POST",
  });
  return parseOrThrow(response, "Cancellation");
}

export async function getInstallation(requestId: string): Promise<InstallationRequest> {
  const response = await fetch(`${API_BASE_URL}/api/installations/${requestId}`);
  return parseOrThrow(response, "Installation lookup");
}
