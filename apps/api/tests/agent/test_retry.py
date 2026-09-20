import pytest
from services.agent.providers.base import AIProviderError, AIProviderErrorCode
from services.agent.retry import call_with_retry


async def test_retries_transient_error_then_succeeds():
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise AIProviderError("temporary", code=AIProviderErrorCode.UNAVAILABLE)
        return "ok"

    result = await call_with_retry(flaky, max_attempts=3, base_delay_seconds=0.001)

    assert result == "ok"
    assert attempts["count"] == 2


async def test_gives_up_after_max_attempts():
    attempts = {"count": 0}

    async def always_fails():
        attempts["count"] += 1
        raise AIProviderError("still down", code=AIProviderErrorCode.TIMEOUT)

    with pytest.raises(AIProviderError):
        await call_with_retry(always_fails, max_attempts=3, base_delay_seconds=0.001)

    assert attempts["count"] == 3


async def test_does_not_retry_non_retryable_error():
    attempts = {"count": 0}

    async def bad_key():
        attempts["count"] += 1
        raise AIProviderError("invalid key", code=AIProviderErrorCode.INVALID_API_KEY)

    with pytest.raises(AIProviderError):
        await call_with_retry(bad_key, max_attempts=3, base_delay_seconds=0.001)

    assert attempts["count"] == 1
