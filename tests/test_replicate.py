import json
import subprocess

import httpx
import pytest

from studio.models import Aspect, Scene, Script
from studio.providers.base import ProviderError, probe_duration
from studio.providers.replicate_video import ReplicateVideo

SCRIPT = Script(
    title="t",
    scenes=[
        Scene(caption="Hello there", narration="Hello there", visual="a bottle on a table"),
        Scene(caption="Buy now", narration="Buy now friends", visual="a smiling customer"),
    ],
)


@pytest.fixture
def sample_clip(tmp_path):
    clip = tmp_path / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "testsrc=size=1280x720:rate=24:duration=1", "-pix_fmt", "yuv420p", str(clip)],
        check=True,
    )  # fmt: skip
    return clip.read_bytes()


@pytest.fixture
def voice(tmp_path):
    path = tmp_path / "voice.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", "3", str(path)],
        check=True,
    )  # fmt: skip
    return path


def make_provider(handler, settings, **overrides):
    kwargs = dict(
        token="r8_secret", model="google/veo-3.1-fast", extra_input={"generate_audio": False},
        clip_seconds=8, timeout_s=5, max_clips=6, ffmpeg_bin="ffmpeg", ffprobe_bin="ffprobe",
        font_file=settings.font_file, poll_interval_s=0,
        transport=httpx.MockTransport(handler),
    )  # fmt: skip
    kwargs.update(overrides)
    return ReplicateVideo(**kwargs)


async def test_generates_clips_and_composes_video(tmp_path, settings, voice, sample_clip):
    created: list[dict] = []
    polls: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer r8_secret"
        url = str(request.url)
        if request.method == "POST":
            assert url == "https://api.replicate.com/v1/models/google/veo-3.1-fast/predictions"
            body = json.loads(request.content)
            created.append(body["input"])
            pid = f"p{len(created)}"
            return httpx.Response(201, json={
                "id": pid, "status": "starting",
                "urls": {"get": f"https://api.replicate.com/v1/predictions/{pid}",
                         "cancel": f"https://api.replicate.com/v1/predictions/{pid}/cancel"},
            })  # fmt: skip
        if url.startswith("https://api.replicate.com/v1/predictions/"):
            pid = url.rsplit("/", 1)[1]
            polls[pid] = polls.get(pid, 0) + 1
            status = "processing" if polls[pid] == 1 else "succeeded"
            output = f"https://replicate.delivery/{pid}.mp4" if status == "succeeded" else None
            return httpx.Response(200, json={"id": pid, "status": status, "output": output,
                                             "urls": {"get": url}})  # fmt: skip
        assert url.startswith("https://replicate.delivery/")
        return httpx.Response(200, content=sample_clip)

    out = tmp_path / "out.mp4"
    await make_provider(handler, settings).render(SCRIPT, voice, out, Aspect.VERTICAL)

    assert [c["prompt"] for c in created] == ["a bottle on a table", "a smiling customer"]
    assert all(c["aspect_ratio"] == "9:16" and c["duration"] == 8 for c in created)
    assert all(c["generate_audio"] is False for c in created)
    assert abs(await probe_duration("ffprobe", out) - 3.0) < 0.3
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert probe.stdout.strip() == "720,1280"


async def test_failed_prediction_surfaces_reason_without_token(tmp_path, settings, voice):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "failed", "error": "NSFW content detected",
                                         "urls": {"get": "https://api.replicate.com/v1/predictions/x"}})  # fmt: skip

    with pytest.raises(ProviderError) as exc:
        await make_provider(handler, settings).render(SCRIPT, voice, tmp_path / "o.mp4", Aspect.WIDE)
    assert "NSFW content detected" in str(exc.value)
    assert "r8_secret" not in str(exc.value)


async def test_http_error_is_reported(tmp_path, settings, voice):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"detail": "Insufficient credit"})

    with pytest.raises(ProviderError, match="HTTP 402: Insufficient credit"):
        await make_provider(handler, settings).render(SCRIPT, voice, tmp_path / "o.mp4", Aspect.WIDE)


async def test_too_many_scenes_fails_before_any_request(tmp_path, settings, voice):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be made")

    with pytest.raises(ProviderError, match="limit is 1"):
        await make_provider(handler, settings, max_clips=1).render(
            SCRIPT, voice, tmp_path / "o.mp4", Aspect.WIDE
        )


async def test_foreign_output_host_never_receives_token(tmp_path, settings, voice):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"status": "succeeded", "output": "https://evil.example/x.mp4",
                                             "urls": {"get": "https://api.replicate.com/v1/predictions/x"}})  # fmt: skip
        raise AssertionError("must not download from a foreign host")

    with pytest.raises(ProviderError, match="unexpected output location"):
        await make_provider(handler, settings).render(SCRIPT, voice, tmp_path / "o.mp4", Aspect.WIDE)


async def test_timeout_cancels_prediction(tmp_path, settings, voice):
    cancelled: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/cancel"):
            cancelled.append(url)
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"status": "processing",
                                         "urls": {"get": "https://api.replicate.com/v1/predictions/x",
                                                  "cancel": "https://api.replicate.com/v1/predictions/x/cancel"}})  # fmt: skip

    with pytest.raises(ProviderError, match="timed out"):
        await make_provider(handler, settings, timeout_s=0).render(
            SCRIPT, voice, tmp_path / "o.mp4", Aspect.WIDE
        )
    assert cancelled


def test_requires_token_and_valid_model(settings):
    with pytest.raises(ProviderError, match="REPLICATE_API_TOKEN"):
        make_provider(lambda r: None, settings, token="")
    with pytest.raises(ProviderError, match="owner/name"):
        make_provider(lambda r: None, settings, model="nope")
