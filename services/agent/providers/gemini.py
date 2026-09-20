"""Google Gemini implementation of AIProvider.

The API key is read strictly from the environment (never accepted as a
request parameter, never logged, never forwarded to the frontend).
"""

from collections.abc import AsyncIterator

from services.agent.providers.base import (
    AIProvider,
    AIProviderError,
    CompletionResult,
    Message,
)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise AIProviderError(
                "GEMINI_API_KEY is not set. Set it in the environment before using the "
                "gemini provider."
            )
        self._api_key = api_key
        self._model = model
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
                system_prompt = message.content
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        return system_prompt, contents

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        client = self._get_client()
        system_prompt, contents = self._to_contents(messages)
        try:
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config={
                    "temperature": temperature,
                    **({"system_instruction": system_prompt} if system_prompt else {}),
                },
            )
        except Exception as exc:  # pragma: no cover - network/SDK failure path
            raise AIProviderError(f"Gemini completion failed: {exc}") from exc

        return CompletionResult(
            text=response.text or "",
            model=self._model,
            provider=self.name,
            raw={},
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        client = self._get_client()
        system_prompt, contents = self._to_contents(messages)
        try:
            stream = await client.aio.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config={
                    "temperature": temperature,
                    **({"system_instruction": system_prompt} if system_prompt else {}),
                },
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # pragma: no cover - network/SDK failure path
            raise AIProviderError(f"Gemini streaming failed: {exc}") from exc
