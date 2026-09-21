# Deployment Guide

This document covers deploying the Cyber AI System backend (`apps/api`),
frontend (`apps/web`), and — optionally — the Android shell and Termux
connector for authorized operators.

## Architecture recap

```
       Browser / Android WebView Shell         Termux (Android device)
                    │                                    │
                    │ HTTPS                              │ WSS
                    ▼                                    ▼
              apps/web (Next.js)     ◄──── apps/api (FastAPI) ────► PostgreSQL
                                              │
                                              ├─ Gemini AI provider
                                              ├─ TerminalEngine (local adapters)
                                              └─ Trusted Tool Registry
```

## Prerequisites

- Python 3.11+
- Node.js 20+ / npm
- PostgreSQL 15+
- A domain with valid TLS (Let's Encrypt is fine)
- A Gemini API key (from Google AI Studio)

## Environment variables

Copy `.env.example` from the repo root and fill in:

```
ENVIRONMENT=production
API_SECRET_KEY=<64-char random>
DATABASE_URL=postgresql+asyncpg://cyberai:<pw>@localhost:5432/cyberai
AI_PROVIDER=gemini
GEMINI_API_KEY=<your key>
GEMINI_MODEL=gemini-3.6-flash
API_CORS_ORIGINS=https://cyberai.yourhost.com
```

Never commit the filled-in `.env`. The `api_secret_key` field must be
truly random (`openssl rand -hex 32`), never a memorable phrase.

## Database

```bash
cd apps/api
alembic upgrade head
```

This runs migrations 0001–0003 (tools, installation, agent). All three
are additive-only — they never drop or alter tables from earlier phases.

## Backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Behind a reverse proxy (nginx/caddy) terminating TLS. The API refuses
`AI_PROVIDER=mock` when `ENVIRONMENT=production` and refuses
cleartext WebSocket connections regardless.

## Frontend

```bash
cd apps/web
npm ci
NEXT_PUBLIC_API_BASE_URL=https://api.cyberai.yourhost.com \
NEXT_PUBLIC_WS_BASE_URL=wss://api.cyberai.yourhost.com \
npm run build
npm start
```

## Docker Compose (optional)

`docker-compose.yml` at the repo root brings up the whole stack for a
staging deployment. Never expose the containers directly to the
internet — always front them with a proxy that terminates TLS.

## CI / CD

- `.github/workflows/ci.yml` runs backend tests + frontend build + the
  Termux connector's unit tests on every push and PR.
- `.github/workflows/android.yml` builds a debug + unsigned-release APK
  of the Android shell whenever `apps/android_shell/` changes; the
  APKs are downloadable as workflow artifacts.

## Post-deploy checklist

- [ ] Backend `/api/health` returns 200.
- [ ] Frontend home page loads and shows "Connected" for the AI provider.
- [ ] `POST /api/termux/devices/register` returns a pairing code.
- [ ] Terminal Engine session creation returns the expected `platform`
      for the host (LINUX/MACOS/WINDOWS).
- [ ] Alembic migrations show all three (`alembic current`).
