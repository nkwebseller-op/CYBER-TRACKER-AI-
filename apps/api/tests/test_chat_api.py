import pytest
from services.agent.providers.base import (
    AIProviderError,
    AIProviderErrorCode,
    ProviderHealth,
    ProviderHealthStatus,
)

from app.api.routes import ai as ai_routes
from app.api.routes import chat as chat_routes
from tests.fakes import FakeProvider, valid_ai_response_payload


@pytest.fixture(autouse=True)
def _isolated_provider_cache():
    yield


async def test_chat_message_success(client, monkeypatch):
    payload = valid_ai_response_payload(conversation_id="conv-http")
    fake = FakeProvider(structured_responses=[payload])
    monkeypatch.setattr(chat_routes, "_get_configured_provider", lambda: fake)

    response = await client.post(
        "/api/chat/message",
        json={"conversationId": "conv-http", "message": "Analyze my authorized API."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["taskPlan"]["conversationId"] == "conv-http"
    assert body["message"]["role"] == "assistant"
    assert body["taskIntent"]["authorizationStatus"] == "UNKNOWN"


async def test_chat_message_rejects_empty_message(client, monkeypatch):
    fake = FakeProvider(structured_responses=[])
    monkeypatch.setattr(chat_routes, "_get_configured_provider", lambda: fake)

    response = await client.post(
        "/api/chat/message", json={"conversationId": "conv-1", "message": "   "}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "empty_message"


async def test_chat_message_returns_502_on_provider_failure(client, monkeypatch):
    # A non-retryable provider error (bad credentials) so this test isn't
    # slowed down by the pipeline's bounded-retry backoff for transient
    # errors — that behavior is covered separately in test_chat_pipeline.py.
    fake = FakeProvider(
        structured_responses=[AIProviderError("down", code=AIProviderErrorCode.INVALID_API_KEY)]
    )
    monkeypatch.setattr(chat_routes, "_get_configured_provider", lambda: fake)

    response = await client.post(
        "/api/chat/message", json={"conversationId": "conv-1", "message": "hello"}
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "api_key" not in detail["message"].lower()


async def test_chat_message_returns_503_when_provider_not_configured(client, monkeypatch):
    def _raise():
        raise AIProviderError("missing key", code=AIProviderErrorCode.MISSING_API_KEY)

    monkeypatch.setattr(chat_routes, "_get_configured_provider", _raise)

    response = await client.post(
        "/api/chat/message", json={"conversationId": "conv-1", "message": "hello"}
    )

    assert response.status_code == 503


async def test_ai_health_reports_connected(client, monkeypatch):
    health = ProviderHealth(provider="fake", status=ProviderHealthStatus.CONNECTED, model="fake-1")
    fake = FakeProvider(health=health)
    monkeypatch.setattr(ai_routes, "get_provider", lambda *args, **kwargs: fake)

    response = await client.get("/api/ai/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["model"] == "fake-1"


async def test_ai_health_reports_not_configured_without_leaking_details(client, monkeypatch):
    def _raise(*args, **kwargs):
        raise AIProviderError(
            "Gemini is selected as the AI provider but no API key is configured.",
            code=AIProviderErrorCode.MISSING_API_KEY,
        )

    monkeypatch.setattr(ai_routes, "get_provider", _raise)

    response = await client.get("/api/ai/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_configured"
    assert "GEMINI_API_KEY" not in (body.get("detail") or "")
