# Architecture

## Pipeline

```
Frontend (Next.js)
    -> API Layer (FastAPI: REST + WebSocket)
    -> Auth / Session Layer
    -> AI Orchestrator            (services/agent)
    -> Task Planner               (services/agent)
    -> Research Engine            (services/research)
    -> Tool Intelligence          (services/tools)
    -> Policy / Authorization     (services/policy)   <-- hard gate, no bypass
    -> Execution Controller       (services/terminal)
    -> Platform Terminal Adapter  (services/terminal/adapters/*)
    -> Result Analyzer            (services/reporting)
    -> Report Engine              (services/reporting)
```

Every stage is a swappable module behind an interface (Python `Protocol` /
abstract base class in the backend, TypeScript interface on the frontend).
Nothing downstream of "AI Orchestrator" trusts model output directly — the
orchestrator only ever emits a `PlannedAction`, a structured, schema-validated
object. Structured actions are the only thing allowed to reach policy and
execution.

## Authorization pipeline (never bypassed)

```
AI intent (unstructured)
  -> PlannedAction (structured, schema-validated)
  -> Policy Engine: static rules (allowed action types, target scope match,
     risk classification)
  -> Authorization check: is the target inside an approved Scope for this
     session? does the action's risk tier require human approval?
  -> Approval gate: auto-approved (low risk, in-scope) or queued for explicit
     user approval (medium/high risk, destructive, or out-of-scope-adjacent)
  -> Execution Controller (only reachable through the above)
  -> Platform Terminal Adapter (never invoked directly by the AI)
  -> Audit Log (append-only, every decision + result recorded)
```

`PolicyDecision` is always one of `ALLOW`, `DENY`, `REQUIRE_APPROVAL`. There
is no code path from AI output to a terminal adapter that does not pass
through `PolicyEngine.evaluate()`. This is enforced at the type level: the
terminal adapters' `execute()` method only accepts an `ApprovedExecution`
object, which can only be constructed by the policy/approval layer.

## Self-healing (error recovery) pipeline

```
ERROR -> classify (services/terminal/recovery/classifier.py)
      -> diagnose (rule-based first; AI-assisted diagnosis later)
      -> propose fix (structured RecoveryAction, same shape as PlannedAction)
      -> policy check (goes through the same PolicyEngine)
      -> approval if required
      -> apply fix (through the same Execution Controller)
      -> retry original action
      -> verify
      -> log
```

Recovery actions are not a side channel — they re-enter the same
policy/approval/execution pipeline as any other action. Phase 1 defines the
`RecoveryAction` schema and the classifier interface; no automatic fixes are
wired to real remediation yet (see `docs/PHASE_1.md`).

## AI provider abstraction

`services/agent/providers/base.py` defines `AIProvider` (async `complete`,
`stream`, `embed`). `services/agent/providers/gemini.py` implements it against
the Google Gemini API. The orchestrator and planner depend only on
`AIProvider`; no other module imports `google.genai` directly. Adding OpenAI/
Anthropic/local models later means adding one file and a config entry — zero
changes to orchestrator, planner, or API routes.

API keys are read from environment variables server-side only
(`GEMINI_API_KEY`) and are never sent to, or readable by, the frontend.

## Data model (Phase 1)

Defined in `apps/api/app/db/models.py`, backed by PostgreSQL via SQLAlchemy
(async) + Alembic migrations:

- `User` / `Session` — auth and session lifecycle
- `Target` — an authorized scope entry (host/domain/IP-range/app), with
  authorization evidence and expiry
- `Task` — a planned unit of work tied to a target and a chat session
- `PlannedAction` — structured action proposed by the AI for a task
- `PolicyDecisionRecord` — the policy engine's verdict on an action, with
  reasoning
- `ExecutionRecord` — what was actually run, on which adapter, with
  stdout/stderr/exit-code and timestamps
- `AuditLogEntry` — append-only trail linking session -> task -> action ->
  decision -> execution
- `Report` / `Finding` — generated output

## Platform terminal adapters

`services/terminal/adapters/{linux,macos,windows,termux}.py` implement a
common `TerminalAdapter` protocol (`run(command_spec) -> ExecutionResult`).
Phase 1 ships the interface, a `LocalProcessAdapter` base using
`asyncio.create_subprocess_exec` (never `shell=True`, never string
concatenation of untrusted input), and adapter selection by
`platform.system()` / Termux detection (`$PREFIX` contains `com.termux`).
Real per-OS tool installation flows are a later phase.

## Why this shape

- **Modularity**: every arrow in the pipeline diagram is an interface, not a
  direct call, so a stage can be replaced (different AI provider, different
  DB, different execution sandbox) without touching its neighbors.
- **No blind execution**: the AI never has a code path to a shell. It can
  only produce data (`PlannedAction`) that other, non-AI code validates.
- **Auditability**: every decision and execution is a database row before it
  happens (decision) and after it happens (result), not just a log line.
