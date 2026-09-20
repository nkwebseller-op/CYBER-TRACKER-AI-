"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import type { StatusState } from "@/components/ui/status-pill";

export interface SystemStatus {
  api: StatusState;
  database: StatusState;
  aiProvider: StatusState;
}

const INITIAL_STATUS: SystemStatus = { api: "unknown", database: "unknown", aiProvider: "unknown" };
const POLL_INTERVAL_MS = 30_000;

/**
 * Polls the backend's own health endpoints — never assumes "connected"
 * just because the frontend rendered. GET /api/health/ready reports API +
 * database; GET /api/ai/health reports the configured AI provider (see
 * apps/api/app/api/routes/ai.py) without ever exposing its API key.
 */
export function useSystemStatus(): SystemStatus {
  const [status, setStatus] = useState<SystemStatus>(INITIAL_STATUS);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      const [readyResult, aiResult] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/health/ready`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE_URL}/api/ai/health`).then((r) => (r.ok ? r.json() : null)),
      ]);

      if (cancelled) return;

      const ready = readyResult.status === "fulfilled" ? readyResult.value : null;
      const ai = aiResult.status === "fulfilled" ? aiResult.value : null;

      setStatus({
        api: ready ? (ready.status === "ok" ? "ok" : "degraded") : "down",
        database: ready ? (ready.status === "ok" ? "ok" : "down") : "unknown",
        aiProvider: mapAiProviderStatus(ai?.status),
      });
    }

    poll();
    const interval = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return status;
}

function mapAiProviderStatus(rawStatus: string | undefined): StatusState {
  switch (rawStatus) {
    case "connected":
      return "ok";
    case "not_configured":
    case "configuration_error":
      return "down";
    case "unavailable":
      return "degraded";
    default:
      return "unknown";
  }
}
