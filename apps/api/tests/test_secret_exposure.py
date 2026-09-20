"""Explicit secret-exposure regression tests (Phase 4 test requirement
#12). These exercise the real GeminiProvider + /api/ai/health wiring with
a fake google.genai.Client — no real network call, no real API key — and
assert the configured "secret" value never appears anywhere in the
response, logs, or exception text.
"""

from google.genai import errors as genai_errors
from services.agent.providers.factory import get_provider

from app.core.config import get_settings

FAKE_SECRET = "sk-super-secret-value-should-never-leak-123456"


class _FakeReplayResponse:
    def __init__(self, error: dict | None = None) -> None:
        self.body_segments = [{"error": error or {}}]


class _FakeModelsAPI:
    def __init__(self, *, get_error: Exception | None = None) -> None:
        self._get_error = get_error

    async def get(self, **kwargs):
        if self._get_error:
            raise self._get_error
        return object()

    async def generate_content(self, **kwargs):  # pragma: no cover - unused here
        raise AssertionError("not expected in this test")


class _FakeAio:
    def __init__(self, models: _FakeModelsAPI) -> None:
        self.models = models


class _FakeGenaiClient:
    def __init__(self, models: _FakeModelsAPI) -> None:
        self.aio = _FakeAio(models)


async def test_api_key_never_appears_in_health_response_body(client, monkeypatch):
    get_settings.cache_clear()
    get_provider.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_SECRET)
    get_settings.cache_clear()

    import google.genai as genai_module

    auth_error = genai_errors.APIError(code=401, response=_FakeReplayResponse())
    fake_models = _FakeModelsAPI(get_error=auth_error)
    monkeypatch.setattr(genai_module, "Client", lambda api_key: _FakeGenaiClient(fake_models))

    response = await client.get("/api/ai/health")

    assert response.status_code == 200
    assert FAKE_SECRET not in response.text
    get_settings.cache_clear()
    get_provider.cache_clear()


async def test_api_key_never_appears_in_chat_error_response(client, monkeypatch):
    get_settings.cache_clear()
    get_provider.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_SECRET)
    get_settings.cache_clear()

    import google.genai as genai_module

    server_error = genai_errors.APIError(code=500, response=_FakeReplayResponse())

    class _GenErrorModels(_FakeModelsAPI):
        async def generate_content(self, **kwargs):
            raise server_error

    monkeypatch.setattr(genai_module, "Client", lambda api_key: _FakeGenaiClient(_GenErrorModels()))

    response = await client.post(
        "/api/chat/message", json={"conversationId": "conv-secret-test", "message": "hello"}
    )

    assert FAKE_SECRET not in response.text
    get_settings.cache_clear()
    get_provider.cache_clear()
