import pytest
from services.agent.providers.base import AIProviderError
from services.agent.providers.factory import get_provider
from services.agent.providers.gemini import GeminiProvider
from services.agent.providers.mock import MockProvider


def test_factory_returns_mock_provider():
    get_provider.cache_clear()
    provider = get_provider("mock", "", "unused-model")
    assert isinstance(provider, MockProvider)


def test_factory_returns_gemini_provider_when_key_present():
    get_provider.cache_clear()
    provider = get_provider("gemini", "test-key", "gemini-2.5-flash")
    assert isinstance(provider, GeminiProvider)


def test_factory_raises_on_missing_gemini_key():
    get_provider.cache_clear()
    with pytest.raises(AIProviderError):
        get_provider("gemini", "", "gemini-2.5-flash")


def test_factory_rejects_unknown_provider():
    get_provider.cache_clear()
    with pytest.raises(AIProviderError):
        get_provider("some-other-provider", "key", "model")
