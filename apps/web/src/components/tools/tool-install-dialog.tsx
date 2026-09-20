"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Badge } from "@/components/ui/badge";
import {
  approveInstallation,
  checkReadiness,
  requestInstallation,
  startInstallation,
} from "@/lib/installation-api";
import type { InstallationRequest, ReadinessReport } from "@/types/installation";
import type { RegistryTool } from "@/types/tools";

type Stage = "form" | "readiness" | "plan" | "installing" | "result";

/**
 * Real backend-driven install flow (Phase 11): readiness check -> plan ->
 * approval (when required) -> start. `start` currently runs synchronously
 * on the backend and returns the final state — there is no live
 * step-by-step stream yet (see services/installation/service.py), so this
 * dialog shows genuine before/after state rather than a fabricated
 * progress bar.
 */
export function ToolInstallDialog({
  tool,
  isOpen,
  onClose,
}: {
  tool: RegistryTool;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [targetId, setTargetId] = useState("");
  const [platform, setPlatform] = useState(tool.supportedPlatforms[0] ?? "");
  const [stage, setStage] = useState<Stage>("form");
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [request, setRequest] = useState<InstallationRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function reset() {
    setStage("form");
    setReadiness(null);
    setRequest(null);
    setError(null);
  }

  async function handleCheckReadiness() {
    setBusy(true);
    setError(null);
    try {
      const report = await checkReadiness(tool.id, targetId, platform);
      setReadiness(report);
      setStage("readiness");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRequestPlan() {
    setBusy(true);
    setError(null);
    try {
      const created = await requestInstallation(tool.id, targetId, platform);
      setRequest(created);
      setStage("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleApprove() {
    if (!request) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await approveInstallation(request.id, "operator");
      setRequest(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    if (!request) return;
    setBusy(true);
    setError(null);
    setStage("installing");
    try {
      const finished = await startInstallation(request.id, targetId);
      setRequest(finished);
      setStage("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStage("plan");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Install ${tool.displayName}`}
      isOpen={isOpen}
      onClose={() => {
        reset();
        onClose();
      }}
    >
      <div className="space-y-4">
        {error && (
          <p className="rounded-md border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger">
            {error}
          </p>
        )}

        {stage === "form" && (
          <>
            <Field
              label="Target ID"
              htmlFor="install-target-id"
              hint="The authorized Target this installation is scoped to."
            >
              <Input
                id="install-target-id"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="UUID of an authorized target"
              />
            </Field>
            <Field label="Platform" htmlFor="install-platform">
              <select
                id="install-platform"
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full rounded-md border border-border-strong bg-surface-raised px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
              >
                {tool.supportedPlatforms.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCheckReadiness}
                disabled={!targetId || !platform || busy}
              >
                Check readiness
              </Button>
            </div>
          </>
        )}

        {stage === "readiness" && readiness && (
          <>
            <div className="space-y-1.5">
              {readiness.checks.map((c) => (
                <div key={c.name} className="flex items-center justify-between text-xs">
                  <span className="text-muted">{c.detail}</span>
                  <Badge
                    tone={
                      c.status === "PASS" ? "accent" : c.status === "FAIL" ? "danger" : "warning"
                    }
                  >
                    {c.status}
                  </Badge>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
              <Button variant="primary" onClick={handleRequestPlan} disabled={!readiness.ready || busy}>
                Generate installation plan
              </Button>
            </div>
          </>
        )}

        {stage === "plan" && request && (
          <>
            <Badge tone="info">{request.state}</Badge>
            {request.plan && (
              <div className="space-y-1 text-xs text-muted">
                <p>Package manager: {request.plan.packageManager}</p>
                <p>Risk level: {request.plan.riskLevel}</p>
                {request.plan.estimatedChanges.map((change) => (
                  <p key={change}>• {change}</p>
                ))}
              </div>
            )}
            {request.state === "WAITING_FOR_APPROVAL" && (
              <Button variant="primary" onClick={handleApprove} disabled={busy}>
                Approve installation
              </Button>
            )}
            {request.state === "PREPARING" && (
              <Button variant="primary" onClick={handleStart} disabled={busy}>
                Start installation
              </Button>
            )}
            {request.state === "BLOCKED" && (
              <p className="text-xs text-danger">{request.errorMessage}</p>
            )}
          </>
        )}

        {stage === "installing" && <p className="text-sm text-muted">Installing…</p>}

        {stage === "result" && request && (
          <>
            <Badge tone={request.state === "INSTALLED" ? "accent" : "danger"}>
              {request.state}
            </Badge>
            {request.verification && (
              <p className="text-xs text-muted">
                Verification: {request.verification.verified ? "confirmed" : "not confirmed"}
              </p>
            )}
            {request.errorMessage && <p className="text-xs text-danger">{request.errorMessage}</p>}
            <div className="flex justify-end">
              <Button variant="primary" onClick={onClose}>
                Done
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
