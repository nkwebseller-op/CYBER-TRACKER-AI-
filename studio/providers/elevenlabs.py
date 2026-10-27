from __future__ import annotations

from pathlib import Path

import httpx

from .base import ProviderError

_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsVoice:
    """Text-to-speech through the ElevenLabs REST API. Usage is billed to your own key."""

    def __init__(self, api_key: str, default_voice_id: str, model_id: str) -> None:
        if not api_key:
            raise ProviderError("ELEVENLABS_API_KEY is not set")
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._model_id = model_id

    async def synthesize(self, text: str, out_dir: Path, voice: str | None) -> Path:
        voice_id = voice or self._default_voice_id
        if not voice_id:
            raise ProviderError("Choose a voice or set ELEVENLABS_VOICE_ID")
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                _URL.format(voice_id=voice_id),
                headers={"xi-api-key": self._api_key, "accept": "audio/mpeg"},
                json={"text": text, "model_id": self._model_id},
            )
        if resp.status_code != 200:
            # Do not echo the response body wholesale; it can contain account details.
            raise ProviderError(f"ElevenLabs returned HTTP {resp.status_code}")
        out = out_dir / "voice.mp3"
        out.write_bytes(resp.content)
        return out
