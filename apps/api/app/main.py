"""FastAPI application entrypoint.

Adds the repository root to sys.path so the `services.*` packages
(the service-boundary modules living outside apps/api, per the monorepo
layout in docs/ARCHITECTURE.md) are importable regardless of the process's
working directory.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from collections.abc import AsyncIterator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI, WebSocket  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.router import api_router  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.errors import CyberAIError, cyberai_error_handler  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.ws.gateway import websocket_endpoint  # noqa: E402

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("api_starting", environment=settings.environment, ai_provider=settings.ai_provider)
    yield


app = FastAPI(
    title="Cyber AI System API",
    version="0.1.0",
    description="Authorized cybersecurity operations platform — API layer.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(CyberAIError, cyberai_error_handler)
app.include_router(api_router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket_endpoint(websocket)
