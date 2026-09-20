"""Provider selection. The only place that branches on a provider name."""

from functools import lru_cache

from services.agent.providers.base import AIProvider, AIProviderError


@lru_cache
def get_provider(provider_name: str, api_key: str, model: str) -> AIProvider:
    if provider_name == "gemini":
        from services.agent.providers.gemini import GeminiProvider

        return GeminiProvider(api_key=api_key, model=model)

    raise AIProviderError(f"Unknown AI provider: {provider_name!r}")
