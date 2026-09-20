"""Conservative, bounded retry for AIProvider calls.

Only retries errors classified as transient (see
AIProviderError.retryable / RETRYABLE_ERROR_CODES in providers/base.py) —
never a bad API key, a bad request, or a validation failure. Uses a short,
capped exponential backoff so a flaky call doesn't turn into a long hang or
a burst of repeated requests against a rate limit.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

from services.agent.providers.base import AIProviderError

T = TypeVar("T")

logger = structlog.get_logger(__name__)


async def call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.5,
    max_delay_seconds: float = 4.0,
    operation: str = "ai_provider_call",
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_error: AIProviderError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except AIProviderError as exc:
            last_error = exc
            is_last_attempt = attempt == max_attempts

            if not exc.retryable or is_last_attempt:
                logger.warning(
                    "ai_provider_call_failed",
                    operation=operation,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_code=exc.code,
                    retryable=exc.retryable,
                    giving_up=True,
                )
                raise

            delay = min(base_delay_seconds * (2 ** (attempt - 1)), max_delay_seconds)
            logger.info(
                "ai_provider_call_retrying",
                operation=operation,
                attempt=attempt,
                max_attempts=max_attempts,
                error_code=exc.code,
                delay_seconds=delay,
            )
            await asyncio.sleep(delay)

    # Unreachable, but keeps the type checker happy and fails loudly if the
    # loop logic above is ever changed incorrectly.
    assert last_error is not None
    raise last_error
