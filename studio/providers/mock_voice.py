from __future__ import annotations

from pathlib import Path

from .base import run_process

_WORDS_PER_SECOND = 2.5


class MockVoice:
    """Writes silence sized to the narration so the whole pipeline runs without a TTS key."""

    def __init__(self, ffmpeg_bin: str) -> None:
        self._ffmpeg = ffmpeg_bin

    async def synthesize(self, text: str, out_dir: Path, voice: str | None) -> Path:
        out = out_dir / "voice.wav"
        seconds = max(2.0, len(text.split()) / _WORDS_PER_SECOND)
        await run_process(
            self._ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "anullsrc=r=24000:cl=mono", "-t", f"{seconds:.2f}", str(out),
        )  # fmt: skip
        return out
