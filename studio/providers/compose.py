"""ffmpeg helpers shared by every video provider: timing, captions, concat, voiceover mux."""

from __future__ import annotations

import textwrap
from pathlib import Path

from ..models import Aspect, Script
from .base import run_process

FPS = 30


def scene_durations(script: Script, total: float) -> list[float]:
    """Split the voiceover length across scenes in proportion to their narration length."""
    weights = [max(1, len(s.narration.split())) for s in script.scenes]
    return [max(0.8, total * w / sum(weights)) for w in weights]


def write_caption(directory: Path, index: int, caption: str, aspect: Aspect) -> Path:
    wrap_at = {Aspect.VERTICAL: 14, Aspect.SQUARE: 22, Aspect.WIDE: 34}[aspect]
    path = directory / f"caption{index}.txt"
    path.write_text("\n".join(textwrap.wrap(caption, wrap_at)), "utf-8")
    return path


def drawtext(text_file: Path, font_file: str, height: int, *, bottom: bool) -> str:
    # The boxed bottom position keeps captions readable over real footage.
    y = "h-text_h-h/10" if bottom else "(h-text_h)/2"
    box = ":box=1:boxcolor=black@0.55:boxborderw=18" if bottom else ""
    out = (
        f"drawtext=textfile={text_file}:fontcolor=white:fontsize={height // 18}"
        f":line_spacing=14:x=(w-text_w)/2:y={y}{box}:alpha='min(1,t/0.4)'"
    )
    return out + (f":fontfile={font_file}" if font_file else "")


async def concat_and_mux(
    ffmpeg_bin: str, segments: list[Path], voice_path: Path, out_path: Path, work_dir: Path
) -> None:
    concat_list = work_dir / "list.txt"
    concat_list.write_text("".join(f"file '{s}'\n" for s in segments), "utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await run_process(
        ffmpeg_bin, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-i", str(voice_path), "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out_path),
    )  # fmt: skip
