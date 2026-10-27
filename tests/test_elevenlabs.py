import json

import httpx
import pytest

from studio.providers.base import ProviderError
from studio.providers.elevenlabs import ElevenLabsVoice


def provider(handler, voice_id="default123"):
    return ElevenLabsVoice("xi_secret", voice_id, "eleven_multilingual_v2", httpx.MockTransport(handler))


async def test_synthesize_posts_expected_request_and_saves_audio(tmp_path):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(path=request.url.path, key=request.headers["xi-api-key"], body=json.loads(request.content))
        return httpx.Response(200, content=b"ID3fake-mp3")

    out = await provider(handler).synthesize("Hello world", tmp_path, "abc_DEF-1")
    assert out.name == "voice.mp3" and out.read_bytes() == b"ID3fake-mp3"
    assert seen["path"] == "/v1/text-to-speech/abc_DEF-1"
    assert seen["key"] == "xi_secret"
    assert seen["body"] == {"text": "Hello world", "model_id": "eleven_multilingual_v2"}


async def test_falls_back_to_default_voice(tmp_path):
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, content=b"x")

    await provider(handler).synthesize("hi", tmp_path, None)
    assert paths == ["/v1/text-to-speech/default123"]


async def test_error_hides_response_body(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": {"message": "key sk_live_abc invalid"}})

    with pytest.raises(ProviderError) as exc:
        await provider(handler).synthesize("hi", tmp_path, None)
    assert str(exc.value) == "ElevenLabs returned HTTP 401"


@pytest.mark.parametrize("bad", ["../v1/user", "a/b", "a b", "x" * 65, "a?b=1"])
async def test_rejects_unsafe_voice_ids(tmp_path, bad):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be made")

    with pytest.raises(ProviderError, match="invalid characters"):
        await provider(handler).synthesize("hi", tmp_path, bad)


async def test_list_voices_maps_id_and_name():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/voices"
        return httpx.Response(200, json={"voices": [{"voice_id": "v1", "name": "Rachel"}, {"voice_id": "v2"}]})

    assert await provider(handler).list_voices() == [
        {"id": "v1", "name": "Rachel"},
        {"id": "v2", "name": "v2"},
    ]


def test_requires_key():
    with pytest.raises(ProviderError):
        ElevenLabsVoice("", "voice", "model")
