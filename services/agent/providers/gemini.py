"""Google Gemini implementation of AIProvider.

The API key is read strictly from the environment (never accepted as a
request parameter, never logged, never forwarded to the frontend, never
included in any exception message raised from this module).
"""

import asyncio
from collections.abc import AsyncIterator

import structlog
from google.genai import errors as genai_errors

from services.agent.providers.base import (
    AIProvider,
    AIProviderError,
    AIProviderErrorCode,
    CompletionResult,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    StructuredCompletionResult,
)

logger = structlog.get_logger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0


def _classify_api_error(exc: Exception) -> AIProviderErrorCode:
    """Map a google-genai exception to our error taxonomy. Never includes
    the exception's raw text in what we return — only the classification."""
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if code in (401, 403):
            return AIProviderErrorCode.INVALID_API_KEY
        if code == 429:
            return AIProviderErrorCode.RATE_LIMITED
        if code is not None and code >= 500:
            return AIProviderErrorCode.UNAVAILABLE
        return AIProviderErrorCode.INVALID_RESPONSE
    if isinstance(exc, TimeoutError | asyncio.TimeoutError):
        return AIProviderErrorCode.TIMEOUT
    if isinstance(exc, ConnectionError | OSError):
        return AIProviderErrorCode.NETWORK_ERROR
    return AIProviderErrorCode.UNKNOWN


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_tokens: int | None = None,
    ) -> None:
        if not api_key:
            raise AIProviderError(
                "Gemini is selected as the AI provider but no API key is configured.",
                code=AIProviderErrorCode.MISSING_API_KEY,
            )
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._client = None  # lazily constructed; see _get_client

    def _get_client(self):
        if self._client is None:
            from google import genai  # imported lazily so importing this module never

            # requires the SDK to be installed unless gemini is actually selected.
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @staticmethod
    def _to_contents(messages: list[Message]) -> tuple[str | None, list[dict]]:
        system_prompt = None
        contents: list[dict] = []
        for message in messages:
            if message.role == "system":
                # Multiple system-role messages (e.g. the fixed instruction
                # plus an application-context block) are joined, not
                # overwritten — see services/agent/prompts.py.
                system_prompt = (
                    f"{system_prompt}\n\n{message.content}" if system_prompt else message.content
                )
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        return system_prompt, contents

    async def _run_with_timeout(self, coro, *, operation: str):
        try:
            return await asyncio.wait_for(coro, timeout=self._timeout_seconds)
        except TimeoutError as exc:
            logger.warning(
                "gemini_request_timeout",
                operation=operation,
                timeout_seconds=self._timeout_seconds,
            )
            raise AIProviderError(
                "The AI provider took too long to respond.", code=AIProviderErrorCode.TIMEOUT
            ) from exc
        except genai_errors.APIError as exc:
            error_code = _classify_api_error(exc)
            logger.warning(
                "gemini_api_error",
                operation=operation,
                http_status=getattr(exc, "code", None),
                error_code=error_code,
            )
            raise AIProviderError(_safe_message_for(error_code), code=error_code) from exc
        except (ConnectionError, OSError) as exc:
            logger.warning("gemini_network_error", operation=operation)
            raise AIProviderError(
                "Could not reach the AI provider — please try again.",
                code=AIProviderErrorCode.NETWORK_ERROR,
            ) from exc

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        client = self._get_client()
        system_prompt, contents = self._to_contents(messages)

        response = await self._run_with_timeout(
            client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config={
                    "temperature": temperature,
                    **({"system_instruction": system_prompt} if system_prompt else {}),
                    **(
                        {"max_output_tokens": self._max_output_tokens}
                        if self._max_output_tokens
                        else {}
                    ),
                },
            ),
            operation="complete",
        )

        return CompletionResult(
            text=response.text or "", model=self._model, provider=self.name, raw={}
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        client = self._get_client()
        system_prompt, contents = self._to_contents(messages)
        try:
            stream = await asyncio.wait_for(
                client.aio.models.generate_content_stream(
                    model=self._model,
                    contents=contents,
                    config={
                        "temperature": temperature,
                        **({"system_instruction": system_prompt} if system_prompt else {}),
                    },
                ),
                timeout=self._timeout_seconds,
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except TimeoutError as exc:
            raise AIProviderError(
                "The AI provider took too long to respond.", code=AIProviderErrorCode.TIMEOUT
            ) from exc
        except genai_errors.APIError as exc:
            error_code = _classify_api_error(exc)
            raise AIProviderError(_safe_message_for(error_code), code=error_code) from exc

    async def generate_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> StructuredCompletionResult:
        client = self._get_client()
        system_prompt, contents = self._to_contents(messages)

        response = await self._run_with_timeout(
            client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                    **({"system_instruction": system_prompt} if system_prompt else {}),
                    **(
                        {"max_output_tokens": max_output_tokens or self._max_output_tokens}
                        if (max_output_tokens or self._max_output_tokens)
                        else {}
                    ),
                },
            ),
            operation="generate_structured",
        )

        raw_text = response.text or ""
        import json

        try:
            data = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("gemini_structured_response_not_json", model=self._model)
            raise AIProviderError(
                "The AI provider returned a response that could not be parsed.",
                code=AIProviderErrorCode.INVALID_RESPONSE,
            ) from exc

        if not isinstance(data, dict):
            raise AIProviderError(
                "The AI provider returned an unexpected response shape.",
                code=AIProviderErrorCode.INVALID_RESPONSE,
            )

        return StructuredCompletionResult(
            data=data, raw_text=raw_text, model=self._model, provider=self.name
        )

    async def health_check(self) -> ProviderHealth:
        try:
            client = self._get_client()
        except AIProviderError as exc:
            return ProviderHealth(
                provider=self.name,
                status=ProviderHealthStatus.NOT_CONFIGURED,
                detail=str(exc),
            )

        try:
            await asyncio.wait_for(client.aio.models.get(model=self._model), timeout=5.0)
        except TimeoutError:
            return ProviderHealth(
                provider=self.name,
                status=ProviderHealthStatus.UNAVAILABLE,
                model=self._model,
                detail="Timed out while checking Gemini connectivity.",
            )
        except genai_errors.APIError as exc:
            error_code = _classify_api_error(exc)
            if error_code == AIProviderErrorCode.INVALID_API_KEY:
                return ProviderHealth(
                    provider=self.name,
                    status=ProviderHealthStatus.CONFIGURATION_ERROR,
                    model=self._model,
                    detail="Gemini rejected the configured API key.",
                )
            return ProviderHealth(
                provider=self.name,
                status=ProviderHealthStatus.UNAVAILABLE,
                model=self._model,
                detail="Gemini is temporarily unavailable.",
            )
        except (ConnectionError, OSError):
            return ProviderHealth(
                provider=self.name,
                status=ProviderHealthStatus.UNAVAILABLE,
                model=self._model,
                detail="Could not reach Gemini.",
            )

        return ProviderHealth(
            provider=self.name, status=ProviderHealthStatus.CONNECTED, model=self._model
        )


def _safe_message_for(code: AIProviderErrorCode) -> str:
    return {
        AIProviderErrorCode.INVALID_API_KEY: (
            "The configured AI provider credentials were rejected."
        ),
        AIProviderErrorCode.RATE_LIMITED: (
            "The AI provider is rate-limiting requests. Please try again shortly."
        ),
        AIProviderErrorCode.UNAVAILABLE: "The AI provider is temporarily unavailable.",
        AIProviderErrorCode.INVALID_RESPONSE: "The AI provider returned an unexpected response.",
    }.get(code, "The AI provider request failed.")
