from __future__ import annotations

import asyncio
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse

import httpx

from ..models import Aspect, Scene, Script
from .base import ProviderError, probe_duration, run_process
from .compose import FPS, concat_and_mux, drawtext, scene_durations, write_caption

API = "https://api.replicate.com/v1"
_TERMINAL = {"succeeded", "failed", "canceled"}
_ALLOWED_OUTPUT_HOSTS = ("replicate.delivery", "replicate.com")
_MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024
_PARALLEL_CLIPS = 3


class ReplicateVideo:
    """AI-generated footage: one text-to-video clip per scene via Replicate, then composited.

    Every scene is a paid prediction on your Replicate account. Clips are trimmed or
    looped to the scene length, cropped to the requested format, captioned, and mixed
    with the voiceover. The model's own audio is discarded.
    """

    def __init__(
        self,
        *,
        token: str,
        model: str,
        extra_input: dict[str, Any],
        clip_seconds: int,
        timeout_s: float,
        max_clips: int,
        ffmpeg_bin: str,
        ffprobe_bin: str,
        font_file: str,
        poll_interval_s: float = 3.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not token:
            raise ProviderError("REPLICATE_API_TOKEN is not set")
        if model.count("/") != 1:
            raise ProviderError("REPLICATE_VIDEO_MODEL must look like owner/name")
        self._token = token
        self._model = model
        self._extra = extra_input
        self._clip_seconds = clip_seconds
        self._timeout_s = timeout_s
        self._max_clips = max_clips
        self._ffmpeg = ffmpeg_bin
        self._ffprobe = ffprobe_bin
        self._font = font_file
        self._poll_s = poll_interval_s
        self._transport = transport

    async def render(
        self, script: Script, voice_path: Path, out_path: Path, aspect: Aspect
    ) -> None:
        if not script.scenes:
            raise ProviderError("Script has no scenes")
        # Fail before spending anything rather than after generating half the clips.
        if len(script.scenes) > self._max_clips:
            raise ProviderError(
                f"Script has {len(script.scenes)} scenes; the limit is {self._max_clips} "
                "(REPLICATE_MAX_CLIPS). Shorten the brief or the length."
            )
        total = await probe_duration(self._ffprobe, voice_path)
        durations = scene_durations(script, total)
        width, height = aspect.size
        # Most video models only offer 16:9 and 9:16; square is cropped from wide.
        model_aspect = "9:16" if aspect is Aspect.VERTICAL else "16:9"

        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            slots = asyncio.Semaphore(_PARALLEL_CLIPS)

            async def clip(i: int, scene: Scene) -> Path:
                async with slots:
                    return await self._generate(scene, model_aspect, tmp / f"clip{i}.mp4")

            clips = await asyncio.gather(*(clip(i, s) for i, s in enumerate(script.scenes)))

            segments: list[Path] = []
            for i, scene in enumerate(script.scenes):
                text_file = write_caption(tmp, i, scene.caption, aspect)
                seg = tmp / f"seg{i}.mp4"
                vf = (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},fps={FPS},setsar=1,"
                    + drawtext(text_file, self._font, height, bottom=True)
                )
                await run_process(
                    self._ffmpeg, "-y", "-loglevel", "error", "-stream_loop", "-1",
                    "-i", str(clips[i]), "-t", f"{durations[i]:.3f}", "-an", "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(seg),
                )  # fmt: skip
                segments.append(seg)
            await concat_and_mux(self._ffmpeg, segments, voice_path, out_path, tmp)

    async def _generate(self, scene: Scene, aspect_ratio: str, dest: Path) -> Path:
        body = {
            "input": {
                "prompt": scene.visual or scene.caption,
                "aspect_ratio": aspect_ratio,
                "duration": self._clip_seconds,
                **self._extra,
            }
        }
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(
            headers=headers, timeout=60, transport=self._transport, follow_redirects=False
        ) as client:
            resp = await client.post(
                f"{API}/models/{self._model}/predictions", json=body, headers={"Prefer": "wait=60"}
            )
            if resp.status_code not in (200, 201):
                raise ProviderError(_http_error("Replicate", resp))
            prediction = resp.json()

            deadline = time.monotonic() + self._timeout_s
            while prediction.get("status") not in _TERMINAL:
                if time.monotonic() > deadline:
                    await self._cancel(client, prediction)
                    raise ProviderError("Replicate timed out generating a clip")
                await asyncio.sleep(self._poll_s)
                poll = await client.get(_api_url((prediction.get("urls") or {}).get("get")))
                if poll.status_code != 200:
                    raise ProviderError(_http_error("Replicate", poll))
                prediction = poll.json()

            if prediction["status"] != "succeeded":
                reason = str(prediction.get("error") or prediction["status"])[:300]
                raise ProviderError(f"Replicate could not generate a clip: {reason}")
            await self._download(client, _output_url(prediction.get("output")), dest)
        return dest

    @staticmethod
    async def _cancel(client: httpx.AsyncClient, prediction: dict[str, Any]) -> None:
        # Best effort: stop paying for a run we have given up on.
        try:
            await client.post(_api_url((prediction.get("urls") or {}).get("cancel")))
        except (httpx.HTTPError, ProviderError):
            pass

    @staticmethod
    async def _download(client: httpx.AsyncClient, url: str, dest: Path) -> None:
        written = 0
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                raise ProviderError(_http_error("Clip download", resp))
            with dest.open("wb") as fh:
                async for chunk in resp.aiter_bytes():
                    written += len(chunk)
                    if written > _MAX_DOWNLOAD_BYTES:
                        raise ProviderError("Generated clip is unexpectedly large")
                    fh.write(chunk)


def _output_url(output: Any) -> str:
    url = output[0] if isinstance(output, list) and output else output
    if not isinstance(url, str):
        raise ProviderError("Replicate returned no video output")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    # The bearer token rides along on the download, so only ever send it to Replicate.
    if parsed.scheme != "https" or not host.endswith(_ALLOWED_OUTPUT_HOSTS):
        raise ProviderError("Replicate returned an unexpected output location")
    return url


def _api_url(url: object) -> str:
    # Never send the bearer token to a URL we did not expect.
    if not isinstance(url, str) or not url.startswith(f"{API}/"):
        raise ProviderError("Replicate returned an unexpected status URL")
    return url


def _http_error(service: str, resp: httpx.Response) -> str:
    detail = ""
    try:
        detail = str(resp.json().get("detail") or "")[:200]
    except (ValueError, AttributeError):
        pass
    return f"{service} returned HTTP {resp.status_code}" + (f": {detail}" if detail else "")
