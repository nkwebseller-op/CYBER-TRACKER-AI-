"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import {
  approveAgentAction,
  cancelAgentTask,
  clarifyAgentTask,
  createAgentTask,
  pauseAgentTask,
  rejectAgentAction,
  resumeAgentTask,
  stepAgentTask,
} from "@/lib/agent-api";
import {
  AGENT_PHASE_TO_WORKFLOW_STAGE,
  AGENT_WORKFLOW_STAGES,
  type AgentTask,
} from "@/types/agent";

const TERMINAL_PHASES = new Set(["CANCELLED", "COMPLETED", "FAILED", "BLOCKED"]);
const NEEDS_INPUT_PHASES = new Set(["WAITING_FOR_AUTHORIZATION", "WAITING_FOR_APPROVAL", "PAUSED"]);

/**
 * Autonomous Agent panel (Phase 12): create an objective, watch the agent
 * reason through UNDERSTAND -> RESEARCH -> PLAN -> APPROVE -> PREPARE ->
 * EXECUTE -> ANALYZE -> VERIFY -> REPORT one step at a time, approve/
 * reject/pause/resume/cancel/clarify where the backend state machine
 * requires it. This is additive to the existing static Task Plan preview
 * above it — it never replaces the one-shot chat planning flow.
 */
export function AgentTaskPanel() {
  const [objective, setObjective] = useState("");
  const [target, setTarget] = useState("");
  const [task, setTask] = useState<AgentTask | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clarificationAnswer, setClarificationAnswer] = useState("");

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    const created = await run(() =>
      createAgentTask({
        objective,
        userRequest: objective,
        target: target || undefined,
        authorizationStatus: target ? "UNKNOWN" : "UNKNOWN",
      })
    );
    if (created) setTask(created);
  }

  async function handleStep() {
    if (!task) return;
    const updated = await run(() => stepAgentTask(task.id, {}));
    if (updated) setTask(updated);
  }

  async function handleApprove() {
    if (!task) return;
    const updated = await run(() => approveAgentAction(task.id, "operator"));
    if (updated) setTask(updated);
  }

  async function handleReject() {
    if (!task) return;
    const updated = await run(() => rejectAgentAction(task.id, "Rejected by operator."));
    if (updated) setTask(updated);
  }

  async function handlePauseResume() {
    if (!task) return;
    const updated = await run(() =>
      task.phase === "PAUSED" ? resumeAgentTask(task.id) : pauseAgentTask(task.id)
    );
    if (updated) setTask(updated);
  }

  async function handleCancel() {
    if (!task) return;
    const updated = await run(() => cancelAgentTask(task.id));
    if (updated) setTask(updated);
  }

  async function handleClarify() {
    if (!task || !clarificationAnswer.trim()) return;
    const updated = await run(() => clarifyAgentTask(task.id, clarificationAnswer));
    if (updated) {
      setTask(updated);
      setClarificationAnswer("");
    }
  }

  const activeStage = task ? AGENT_PHASE_TO_WORKFLOW_STAGE[task.phase] : null;
  const isTerminal = task ? TERMINAL_PHASES.has(task.phase) : false;
  const needsInput = task ? NEEDS_INPUT_PHASES.has(task.phase) : false;

  return (
    <Panel
      title="Autonomous Agent"
      subtitle="Stateful, multi-step reasoning over an authorized objective — every action still requires policy/approval before it runs."
    >
      <div className="space-y-4">
        {error && (
          <p className="rounded-md border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger">
            {error}
          </p>
        )}

        {!task && (
          <>
            <Field label="Objective" htmlFor="agent-objective">
              <Input
                id="agent-objective"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="e.g. Run a safe DNS diagnostic on my authorized server"
              />
            </Field>
            <Field
              label="Target (optional)"
              htmlFor="agent-target"
              hint="Leave blank if you'll clarify it once the agent asks."
            >
              <Input
                id="agent-target"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. example-internal.test"
              />
            </Field>
            <Button variant="primary" onClick={handleStart} disabled={!objective.trim() || busy}>
              Start task
            </Button>
          </>
        )}

        {task && (
          <>
            <div className="flex flex-wrap items-center gap-1.5">
              {AGENT_WORKFLOW_STAGES.map((stage) => (
                <span
                  key={stage}
                  className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                    stage === activeStage
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border bg-surface-raised/40 text-muted"
                  }`}
                >
                  {stage}
                </span>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge tone={isTerminal ? (task.phase === "COMPLETED" ? "accent" : "danger") : "info"}>
                {task.phase}
              </Badge>
              <span className="text-muted">{task.objective}</span>
            </div>

            {task.clarificationQuestion && (
              <div className="space-y-2 rounded-md border border-warning/30 bg-warning-soft px-3 py-2">
                <p className="text-xs text-warning">{task.clarificationQuestion}</p>
                <div className="flex gap-2">
                  <Input
                    value={clarificationAnswer}
                    onChange={(e) => setClarificationAnswer(e.target.value)}
                    placeholder="Your answer…"
                  />
                  <Button size="sm" variant="secondary" onClick={handleClarify} disabled={busy}>
                    Send
                  </Button>
                </div>
              </div>
            )}

            {task.actions.length > 0 && (
              <div className="space-y-1.5 text-xs">
                {task.actions.map((action) => (
                  <div key={action.id} className="flex items-center justify-between gap-2">
                    <span className="text-muted-strong">{action.actionType}</span>
                    <span className="truncate text-muted">
                      {action.resultSummary ?? action.errorCategory ?? "pending"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {(task.findings.length > 0 || task.observations.length > 0) && (
              <div className="space-y-1 border-t border-border pt-2 text-xs text-muted">
                {[...task.observations, ...task.findings].slice(-4).map((e) => (
                  <p key={e.id}>
                    [{e.kind}] {e.summary}
                  </p>
                ))}
              </div>
            )}

            <div className="flex flex-wrap gap-2 border-t border-border pt-3">
              {task.phase === "WAITING_FOR_APPROVAL" && (
                <>
                  <Button size="sm" variant="primary" onClick={handleApprove} disabled={busy}>
                    Approve
                  </Button>
                  <Button size="sm" variant="danger" onClick={handleReject} disabled={busy}>
                    Reject
                  </Button>
                </>
              )}
              {!isTerminal && !needsInput && (
                <Button size="sm" variant="secondary" onClick={handleStep} disabled={busy}>
                  Continue
                </Button>
              )}
              {!isTerminal && task.phase !== "WAITING_FOR_APPROVAL" && (
                <Button size="sm" variant="ghost" onClick={handlePauseResume} disabled={busy}>
                  {task.phase === "PAUSED" ? "Resume" : "Pause"}
                </Button>
              )}
              {!isTerminal && (
                <Button size="sm" variant="ghost" onClick={handleCancel} disabled={busy}>
                  Cancel
                </Button>
              )}
              {isTerminal && (
                <Button size="sm" variant="ghost" onClick={() => setTask(null)}>
                  New task
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}
