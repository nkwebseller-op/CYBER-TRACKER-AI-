#!/usr/bin/env bash
# Starts the API and web dev servers together. Requires both toolchains
# installed (see README.md quick start) and .venv already created in
# apps/api.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

(
  cd "$ROOT_DIR/apps/api"
  source .venv/bin/activate
  uvicorn app.main:app --reload --port 8000
) &

(
  cd "$ROOT_DIR/apps/web"
  npm run dev
) &

wait
