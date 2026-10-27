from __future__ import annotations

import re
from pathlib import Path

import httpx

from .base import ProviderError

_BASE = "https://api.elevenlabs.io"
_VOICE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class ElevenLabsVoice:
    """Text-to-speech through the ElevenLabs REST API. Usage is billed to your own key."""

    def __init__(
        self,
        api_key: str,
        default_voice_id: str,
        model_id: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ProviderError("ELEVENLABS_API_KEY is not set")
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._model_id = model_id
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=_BASE,
            timeout=timeout,
            transport=self._transport,
            headers={"xi-api-key": self._api_key},
        )

    async def synthesize(self, text: str, out_dir: Path, voice: str | None) -> Path:
        voice_id = voice or self._default_voice_id
        if not voice_id:
            raise ProviderError("Choose a voice or set ELEVENLABS_VOICE_ID")
        # The id becomes part of the request path, so reject anything that is not a plain id.
        if not _VOICE_ID.fullmatch(voice_id):
            raise ProviderError("Voice ID contains invalid characters")
        async with self._client(120) as client:
            resp = await client.post(
                f"/v1/text-to-speech/{voice_id}",
                headers={"accept": "audio/mpeg"},
                json={"text": text, "model_id": self._model_id},
            )
        if resp.status_code != 200:
            # Do not echo the response body wholesale; it can contain account details.
            raise ProviderError(f"ElevenLabs returned HTTP {resp.status_code}")
        out = out_dir / "voice.mp3"
        out.write_bytes(resp.content)
        return out

    async def list_voices(self) -> list[dict[str, str]]:
        async with self._client(30) as client:
            resp = await client.get("/v2/voices", params={"page_size": 100})
        if resp.status_code != 200:
            raise ProviderError(f"ElevenLabs returned HTTP {resp.status_code}")
        return [
            {"id": v["voice_id"], "name": v.get("name") or v["voice_id"]}
            for v in resp.json().get("voices", [])
        ]
