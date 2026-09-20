from datetime import UTC, datetime

from fastapi import APIRouter

from app.db.session import check_db_connection
from app.schemas.common import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])

SERVICE_VERSION = "0.1.0"


@router.get("", response_model=HealthStatus)
async def liveness() -> HealthStatus:
    return HealthStatus(
        status="ok",
        service="cyberai-api",
        version=SERVICE_VERSION,
        timestamp=datetime.now(UTC),
    )


@router.get("/ready", response_model=HealthStatus)
async def readiness() -> HealthStatus:
    db_ok = await check_db_connection()
    return HealthStatus(
        status="ok" if db_ok else "degraded",
        service="cyberai-api",
        version=SERVICE_VERSION,
        timestamp=datetime.now(UTC),
    )
