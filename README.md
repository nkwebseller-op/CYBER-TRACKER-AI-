# Cyber AI System

AI-powered **authorized** cybersecurity operations platform. A user describes an
authorized security objective in natural language; the system plans, researches
tooling, validates authorization/policy, executes controlled assessment
workflows across platforms, and produces findings/reports.

## Status

All 14 phases of the foundational build are complete:

| Phase | Focus                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------ |
| 1     | Monorepo foundation & shared contracts                                                           |
| 2     | Premium SOC-themed dashboard (Next.js)                                                           |
| 3     | Chat / Command Center (intent extraction, task-plan preview)                                     |
| 4     | Gemini AI provider integration (structured output, JSON-schema-validated)                        |
| 5     | Cross-platform controlled Terminal Engine                                                        |
| 6     | Windows Terminal Adapter (PowerShell)                                                            |
| 7     | Linux Terminal Adapter                                                                           |
| 8     | macOS Terminal Adapter                                                                           |
| 9     | Android / Termux remote connector (backend WebSocket)                                            |
| 10    | Tool Discovery + Trusted Tool Registry                                                           |
| 11    | Tool Installation & Environment Preparation                                                      |
| 12    | Autonomous Agent Orchestrator (stateful multi-step reasoning + voice architecture)               |
| 13    | Self-Healing Engine (structured diagnosis + healing strategies)                                  |
| 14    | Termux connector Python app + Android APK shell + Docker/CI deployment + operator documentation  |

## Monorepo layout

```
apps/
  api/                    FastAPI backend (async) — HTTP + WebSocket gateway
  web/                    Next.js (TypeScript, Tailwind) frontend
  termux_connector/       Python app that runs on Android in Termux (Phase 14)
  android_shell/          Native Kotlin WebView wrapper (Phase 14, built via GH Actions)
packages/
  shared-types/           Cross-language contract source
services/
  agent/                  AI provider abstraction + chat pipeline
  agent_orchestrator/     Autonomous agent (Phase 12)
  self_healing/           Diagnosis + healing strategies (Phase 13)
  policy/                 Policy / Authorization / Risk engine
  terminal/               Platform Terminal Adapters (Win/Linux/macOS)
  termux/                 Termux connection manager + pairing (backend)
  tools/                  Trusted Tool Registry + discovery + verification
  installation/           Tool installation & environment prep (Phase 11)
  reporting/              Report builder
docs/                     Architecture, deployment, Termux and Android setup guides
.github/workflows/        CI + Android APK builds
```

## Quick start (development)

```bash
cp .env.example .env          # fill in secrets locally, never commit .env

# API
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # apply migrations (requires PostgreSQL)
uvicorn app.main:app --reload --port 8000

# Web (separate terminal)
cd apps/web
npm install
npm run dev
```

Or with Docker Compose:

```bash
API_SECRET_KEY=$(openssl rand -hex 32) GEMINI_API_KEY=<your-key> docker compose up
```

## Guides for operators

| I want to…                                            | Read this                            |
| ----------------------------------------------------- | ------------------------------------ |
| Deploy the whole stack to a server                    | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Pair an authorized Android device via Termux          | [docs/TERMUX_SETUP.md](docs/TERMUX_SETUP.md) |
| Install the native Android dashboard shell           | [docs/ANDROID_SETUP.md](docs/ANDROID_SETUP.md) |
| Understand the architecture                           | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

## Health checks

- API: `GET /api/health` (liveness), `GET /api/health/ready` (DB connectivity)
- AI provider: `GET /api/ai/health`
- Web: `GET /api/health`

## Testing

```bash
# Backend
cd apps/api && python -m pytest -q

# Frontend
cd apps/web && npm run lint && npm run build

# Termux connector
cd apps/termux_connector && python -m pytest tests/
```

CI runs all three on every push (`.github/workflows/ci.yml`).

## Security notes

- The AI never generates raw shell commands. It proposes structured
  `ActionType` values that the terminal engine resolves through the
  reviewed template registry (`services/terminal/command_templates.py`).
- Every action goes through the Policy Engine (`services/policy/engine.py`)
  before it can run. There is no bypass.
- Approval flags from the model are only ever upgraded (more cautious),
  never downgraded.
- The Termux connector on the phone re-validates everything the backend
  sends: argv shape, secret-shaped env keys, working-directory scope,
  timeout ceiling. See `apps/termux_connector/cyberai_termux.py`.
- `.env` files are gitignored. API keys never appear in logs, audit
  events, or long-term memory.

Do **not** use this system against targets you are not explicitly
authorized to test.
