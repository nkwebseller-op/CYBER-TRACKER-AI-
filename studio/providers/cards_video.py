from __future__ import annotations

import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

from ..models import Aspect, Script
from .base import ProviderError, probe_duration, run_process

_PALETTE = ("#0f172a", "#7c2d12", "#134e4a", "#4c1d95", "#831843", "#1e3a8a")
_FPS = 30


class CardsVideo:
    """Renders fade-in caption cards timed to the voiceover with ffmpeg.

    This is a real, fully offline renderer, not a generative-video model. A
    generative provider can replace it by implementing `VideoProvider.render`.
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
        weights = [max(1, len(s.narration.split())) for s in script.scenes]
        wrap_at = 14 if aspect is Aspect.VERTICAL else 22 if aspect is Aspect.SQUARE else 34

        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            segments: list[Path] = []
            for i, scene in enumerate(script.scenes):
                seconds = max(0.8, total * weights[i] / sum(weights))
                text_file = tmp / f"scene{i}.txt"
                text_file.write_text("\n".join(textwrap.wrap(scene.caption, wrap_at)), "utf-8")
                seg = tmp / f"seg{i}.mp4"
                drawtext = (
                    f"drawtext=textfile={text_file}:fontcolor=white:fontsize={height // 18}"
                    f":line_spacing=14:x=(w-text_w)/2:y=(h-text_h)/2"
                    f":alpha='min(1,t/0.4)'"
                )
                if self._font:
                    drawtext += f":fontfile={self._font}"
                await run_process(
                    self._ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c={_PALETTE[i % len(_PALETTE)]}:s={width}x{height}:d={seconds:.3f}:r={_FPS}",
                    "-vf", drawtext, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(seg),
                )  # fmt: skip
                segments.append(seg)

            concat_list = tmp / "list.txt"
            concat_list.write_text("".join(f"file '{s}'\n" for s in segments), "utf-8")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            await run_process(
                self._ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-i", str(voice_path), "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                str(out_path),
            )  # fmt: skip
