"""Provider selection. The only place that branches on a provider name.

`AI_PROVIDER=mock` is refused outright when the application is running
with environment=="production" (enforced in app/core/config.py at startup)
so the mock provider can never accidentally become the production
provider — this factory only has to worry about constructing whichever
provider was already validated as allowed.
"""

from functools import lru_cache

from services.agent.providers.base import AIProvider, AIProviderError, AIProviderErrorCode

SUPPORTED_PROVIDERS = frozenset({"gemini", "mock"})


@lru_cache
def get_provider(
    provider_name: str,
    api_key: str,
    model: str,
    *,
    timeout_seconds: float = 30.0,
    max_output_tokens: int | None = None,
) -> AIProvider:
    if provider_name == "gemini":
        from services.agent.providers.gemini import GeminiProvider

        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

    if provider_name == "mock":
        from services.agent.providers.mock import MockProvider

        return MockProvider()

    raise AIProviderError(
        f"Unknown AI provider: {provider_name!r}", code=AIProviderErrorCode.CONFIGURATION_ERROR
    )
