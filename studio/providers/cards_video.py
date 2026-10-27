from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ..models import Aspect, Script
from .base import ProviderError, probe_duration, run_process
from .compose import FPS, concat_and_mux, drawtext, scene_durations, write_caption

_PALETTE = ("#0f172a", "#7c2d12", "#134e4a", "#4c1d95", "#831843", "#1e3a8a")


class CardsVideo:
    """Renders fade-in caption cards timed to the voiceover with ffmpeg.

    This is a real, fully offline renderer, not a generative-video model. Use the
    `replicate` provider for AI-generated footage.
    """

    def __init__(self, ffmpeg_bin: str, ffprobe_bin: str, font_file: str) -> None:
        self._ffmpeg = ffmpeg_bin
        self._ffprobe = ffprobe_bin
        self._font = font_file

    async def render(
        self, script: Script, voice_path: Path, out_path: Path, aspect: Aspect
    ) -> None:
        if not script.scenes:
            raise ProviderError("Script has no scenes")
        total = await probe_duration(self._ffprobe, voice_path)
        width, height = aspect.size
        durations = scene_durations(script, total)

        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            segments: list[Path] = []
            for i, scene in enumerate(script.scenes):
                text_file = write_caption(tmp, i, scene.caption, aspect)
                seg = tmp / f"seg{i}.mp4"
                await run_process(
                    self._ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c={_PALETTE[i % len(_PALETTE)]}:s={width}x{height}"
                    f":d={durations[i]:.3f}:r={FPS}",
                    "-vf", drawtext(text_file, self._font, height, bottom=False),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(seg),
                )  # fmt: skip
                segments.append(seg)
            await concat_and_mux(self._ffmpeg, segments, voice_path, out_path, tmp)
