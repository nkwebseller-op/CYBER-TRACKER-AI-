"""AI provider health endpoint.

Distinguishes "not configured" / "configuration error" / "unavailable" /
"connected" without ever exposing the API key or any other secret. The
frontend's AI Provider status pill polls this.
"""

from fastapi import APIRouter
from services.agent.providers.base import AIProviderError, ProviderHealth, ProviderHealthStatus
from services.agent.providers.factory import get_provider

from app.core.config import get_settings
from app.schemas.ai import AIProviderHealthResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health", response_model=AIProviderHealthResponse)
async def ai_health() -> AIProviderHealthResponse:
    settings = get_settings()

    try:
        provider = get_provider(
            settings.ai_provider,
            settings.gemini_api_key,
            settings.gemini_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
            max_output_tokens=settings.ai_max_output_tokens,
        )
    except AIProviderError as exc:
        return AIProviderHealthResponse(
            provider=settings.ai_provider,
            status=ProviderHealthStatus.NOT_CONFIGURED,
            detail=str(exc),
        )

    health: ProviderHealth = await provider.health_check()
    return AIProviderHealthResponse(
        provider=health.provider,
        status=health.status,
        model=health.model,
        detail=health.detail,
    )
