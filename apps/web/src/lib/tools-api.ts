/**
 * Thin client for the Phase 10 Tool Discovery & Trusted Tool Registry API
 * (apps/api/app/api/routes/tools.py). There is no method here that
 * installs or executes a tool — only listing, lookup, and discovery.
 */

import { API_BASE_URL } from "@/lib/api";
import type { RegistryTool, ToolSelectionProposal } from "@/types/tools";

export interface ListToolsParams {
  category?: string;
  platform?: string;
  trustStatus?: string;
  search?: string;
}

export async function listTools(params: ListToolsParams = {}): Promise<RegistryTool[]> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.platform) query.set("platform", params.platform);
  if (params.trustStatus) query.set("trustStatus", params.trustStatus);
  if (params.search) query.set("search", params.search);

  const response = await fetch(`${API_BASE_URL}/api/tools?${query.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to list tools (${response.status})`);
  }
  return response.json();
}

export async function getTool(toolId: string): Promise<RegistryTool> {
  const response = await fetch(`${API_BASE_URL}/api/tools/${toolId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tool (${response.status})`);
  }
  return response.json();
}

export async function discoverTools(capability: string): Promise<ToolSelectionProposal> {
  const response = await fetch(`${API_BASE_URL}/api/tools/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ capability }),
  });
  if (!response.ok) {
    throw new Error(`Failed to discover tools (${response.status})`);
  }
  return response.json();
}
