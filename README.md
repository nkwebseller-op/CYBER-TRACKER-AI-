# Cyber AI System

AI-powered **authorized** cybersecurity operations platform. A user describes an
authorized security objective in natural language; the system plans, researches
tooling, validates authorization/policy, executes controlled assessment
workflows across platforms, and produces findings/reports.

> **Phase 1 (this state): Foundation & Architecture.**
> No attack modules are implemented yet. This phase establishes the monorepo,
> service boundaries, shared contracts, database schema, AI provider
> abstraction, policy/authorization skeleton, and the web/API shells they run
> in.

## Monorepo layout

```
apps/
  web/            Next.js (TypeScript, Tailwind) frontend
  api/            FastAPI backend (async) — HTTP + WebSocket gateway
packages/
  shared-types/   Cross-language contract source (JSON Schema) + generated TS/Python types
  config/         Shared lint/tsconfig/build configuration
services/
  agent/          AI Orchestrator + Task Planner (Gemini-backed, provider-agnostic)
  research/       Tool/technique research engine
  tools/          Tool Intelligence (compatibility, provenance, install specs)
  policy/         Authorization/Policy/Risk engine — the only path to execution approval
  terminal/       Platform Terminal Adapter (Windows/Linux/macOS/Termux) + Execution Controller
  reporting/      Result Analyzer + Report Engine
infrastructure/  Deployment, database migrations, environment templates
docs/            Architecture, ADRs, phase notes
tests/           Cross-cutting integration tests
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and
[`docs/PHASE_1.md`](docs/PHASE_1.md) for what is and isn't built yet.

## Quick start

```bash
cp .env.example .env          # fill in secrets locally, never commit .env

# API
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Web
cd apps/web
npm install
npm run dev
```

Or from the repo root: `./scripts/dev.sh` (starts both, requires both toolchains).

## Health checks

- API: `GET /api/health` (liveness) and `GET /api/health/ready` (DB connectivity)
- Web: `GET /api/health` (Next.js route)
