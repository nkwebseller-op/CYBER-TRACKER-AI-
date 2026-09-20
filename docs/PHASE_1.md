# Phase 1: Foundation & Architecture — status

## Done

- Monorepo layout (`apps/`, `packages/`, `services/`, `infrastructure/`, `docs/`, `tests/`).
- FastAPI backend (`apps/api`): async, structured logging (structlog), typed
  settings (pydantic-settings), domain error hierarchy with a global
  exception handler, CORS, `/api/health` + `/api/health/ready`.
- PostgreSQL data model via async SQLAlchemy + Alembic
  (`apps/api/app/db/models.py`): users, sessions, targets, tasks, planned
  actions, policy decisions, executions, audit log, reports/findings.
- AI provider abstraction (`services/agent/providers`): `AIProvider`
  interface + Gemini implementation, selected by config, never imported
  directly outside the provider layer. `POST /api/chat` exercises it
  end-to-end (verified manually; returns a clean 502 with no `GEMINI_API_KEY`
  set, rather than crashing).
- Policy/Authorization Engine skeleton (`services/policy/engine.py`) with
  the `ALLOW`/`DENY`/`REQUIRE_APPROVAL` model, target-scope expiry checks,
  and an action-type registry that is empty by design (nothing is
  auto-approved until real action types are reviewed). Covered by tests.
- Execution Controller + platform terminal adapters
  (`services/terminal/*`): Linux/macOS/Windows/Termux adapters over
  `asyncio.create_subprocess_exec` (no shell), gated by
  `ApprovedExecution.from_policy_decision`, which only accepts an `ALLOW`
  verdict or an explicitly approved `REQUIRE_APPROVAL`.
- Self-healing error classifier skeleton
  (`services/terminal/recovery/classifier.py`) with the error taxonomy from
  the architecture doc; no automatic remediation yet (see below).
- Shared contracts (`packages/shared-types`): JSON Schema + TypeScript
  mirrors for `PlannedAction`, `PolicyDecision`, `ExecutionResult`.
- Next.js frontend (`apps/web`, TS + Tailwind + App Router): dark
  emerald-on-black SOC-styled shell with sidebar nav, top status bar, and
  all eight required sections (Dashboard, Chat, Targets, Tasks, Tool
  Discovery, Terminal, Reports, Settings). Chat page is a working client
  calling the real `/api/chat` endpoint; Targets page server-fetches
  `/api/targets`.
- `/api/health` route on both API and web.
- Dev scripts (`scripts/dev.sh`), `.env.example` at repo root and in
  `apps/web`, `.gitignore`.

## Verified locally this session

- `pytest` in `apps/api`: 4/4 passing (health route + policy engine rules).
- `ruff check` clean across `apps/api/app` and `services/`.
- API boots with `uvicorn`, both health endpoints return 200.
- `npm run lint` and `npm run typecheck` clean in `apps/web`.
- `npm run build` succeeds (Next.js production build, all routes compile).
- Both dev servers running together: all UI routes return 200, the Targets
  page fetches live (empty) data from the API, and Chat correctly surfaces a
  provider error instead of crashing when no Gemini key is configured.

## Explicitly NOT built yet (by design — do not skip ahead)

- No real security tools are registered (`services/tools/registry.py` is
  empty) and no action types are registered with the policy engine — so no
  action can currently reach `ALLOW`. This is intentional: there is nothing
  reviewed yet to allow.
- Task Planner does not parse AI output into `PlannedAction` objects; the
  orchestrator only holds a conversation.
- No authentication/session issuance is wired to the API (models exist;
  routes/JWT flow do not).
- WebSocket gateway broadcasts nothing real yet (no execution or AI-activity
  events are published to it).
- No automatic recovery actions are applied — the classifier exists, "propose
  fix" → "apply fix" is not implemented.
- No Alembic migration has been generated yet (models exist; run
  `alembic revision --autogenerate` against a real Postgres instance to
  produce the first migration — this session had no Postgres available to
  verify against, only SQLite for tests).
- No CI workflow file yet (structure supports one: `pytest` + `ruff` for the
  API, `npm run lint`/`typecheck`/`build` for the web app).

## Suggested next phase

1. Generate and commit the first Alembic migration against a real Postgres
   instance.
2. Add auth (JWT issuance, password hashing already scaffolded via
   `passlib`) and wire session creation to `/api/chat`.
3. Define the first 3–5 reviewed, low-risk action types (e.g.
   `recon.dns_lookup`, `web.header_scan`) in `services/tools/registry.py`
   and register them in `services/policy.engine.REGISTERED_ACTION_TYPES`.
4. Extend the Task Planner to turn an orchestrator reply into a
   `PlannedAction`, and wire the API route that submits it through
   `PolicyEngine.evaluate`.
5. Publish real events (execution start/stdout/stderr/finish) to the
   WebSocket hub and consume them in the Terminal page.
