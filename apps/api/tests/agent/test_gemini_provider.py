import asyncio
import json

import pytest
from google.genai import errors as genai_errors
from services.agent.providers.base import (
    AIProviderError,
    AIProviderErrorCode,
    Message,
    ProviderHealthStatus,
)
from services.agent.providers.gemini import GeminiProvider


class FakeReplayResponse:
    """Satisfies google.genai.errors.APIError's non-requests.Response branch."""

    def __init__(self, error: dict | None = None) -> None:
        self.body_segments = [{"error": error or {}}]


class FakeModelsAPI:
    def __init__(
        self,
        *,
        generate_result=None,
        generate_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self._generate_result = generate_result
        self._generate_error = generate_error
        self._get_error = get_error

    async def generate_content(self, **kwargs):
        if self._generate_error:
            raise self._generate_error
        return self._generate_result

    async def get(self, **kwargs):
        if self._get_error:
            raise self._get_error
        return object()


class FakeAio:
    def __init__(self, models: FakeModelsAPI) -> None:
        self.models = models


class FakeGenaiClient:
    def __init__(self, models: FakeModelsAPI) -> None:
        self.aio = FakeAio(models)


class FakeTextResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def _install_fake_client(monkeypatch, models: FakeModelsAPI) -> None:
    import google.genai as genai_module

    monkeypatch.setattr(genai_module, "Client", lambda api_key: FakeGenaiClient(models))


def test_missing_api_key_raises_at_construction():
    with pytest.raises(AIProviderError) as exc_info:
        GeminiProvider(api_key="", model="gemini-2.5-flash")
    assert exc_info.value.code == AIProviderErrorCode.MISSING_API_KEY


async def test_generate_structured_success(monkeypatch):
    payload = {"message": "ok", "taskIntent": {}, "taskPlan": {}}
    _install_fake_client(
        monkeypatch, FakeModelsAPI(generate_result=FakeTextResponse(json.dumps(payload)))
    )

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")
    result = await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert result.data == payload
    assert result.provider == "gemini"


async def test_generate_structured_rejects_non_json_response(monkeypatch):
    models = FakeModelsAPI(generate_result=FakeTextResponse("not json at all"))
    _install_fake_client(monkeypatch, models)

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert exc_info.value.code == AIProviderErrorCode.INVALID_RESPONSE


async def test_invalid_api_key_is_classified_correctly(monkeypatch):
    error = genai_errors.APIError(code=401, response=FakeReplayResponse())
    _install_fake_client(monkeypatch, FakeModelsAPI(generate_error=error))

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert exc_info.value.code == AIProviderErrorCode.INVALID_API_KEY
    assert not exc_info.value.retryable
    assert "test-key" not in str(exc_info.value)


async def test_rate_limit_is_classified_as_retryable(monkeypatch):
    error = genai_errors.APIError(code=429, response=FakeReplayResponse())
    _install_fake_client(monkeypatch, FakeModelsAPI(generate_error=error))

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert exc_info.value.code == AIProviderErrorCode.RATE_LIMITED
    assert exc_info.value.retryable


async def test_server_error_is_classified_as_unavailable_and_retryable(monkeypatch):
    error = genai_errors.APIError(code=503, response=FakeReplayResponse())
    _install_fake_client(monkeypatch, FakeModelsAPI(generate_error=error))

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert exc_info.value.code == AIProviderErrorCode.UNAVAILABLE
    assert exc_info.value.retryable


async def test_timeout_is_classified_and_retryable(monkeypatch):
    async def hangs(**kwargs):
        await asyncio.sleep(10)

    models = FakeModelsAPI()
    models.generate_content = hangs
    _install_fake_client(monkeypatch, models)

    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash", timeout_seconds=0.01)

    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate_structured([Message(role="user", content="hi")], schema={})

    assert exc_info.value.code == AIProviderErrorCode.TIMEOUT
    assert exc_info.value.retryable


async def test_health_check_connected(monkeypatch):
    _install_fake_client(monkeypatch, FakeModelsAPI())
    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    health = await provider.health_check()

    assert health.status == ProviderHealthStatus.CONNECTED
    assert health.provider == "gemini"


async def test_health_check_configuration_error(monkeypatch):
    error = genai_errors.APIError(code=403, response=FakeReplayResponse())
    _install_fake_client(monkeypatch, FakeModelsAPI(get_error=error))
    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    health = await provider.health_check()

    assert health.status == ProviderHealthStatus.CONFIGURATION_ERROR
    assert "test-key" not in (health.detail or "")


async def test_health_check_unavailable_on_server_error(monkeypatch):
    error = genai_errors.APIError(code=500, response=FakeReplayResponse())
    _install_fake_client(monkeypatch, FakeModelsAPI(get_error=error))
    provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")

    health = await provider.health_check()

    assert health.status == ProviderHealthStatus.UNAVAILABLE
