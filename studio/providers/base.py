from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from ..models import Aspect, Script, Tone


class ProviderError(RuntimeError):
    """A provider failed in a way the user should see (bad key, ffmpeg error, ...)."""


class ScriptWriter(Protocol):
    async def write(self, brief: str, tone: Tone, duration_s: int) -> Script: ...


class VoiceProvider(Protocol):
    async def synthesize(self, text: str, out_dir: Path, voice: str | None) -> Path:
        """Write speech for `text` to a `voice.<ext>` file in `out_dir` and return its path."""
        ...


class VideoProvider(Protocol):
    async def render(
        self, script: Script, voice_path: Path, out_path: Path, aspect: Aspect
    ) -> None: ...


async def run_process(*argv: str) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise ProviderError(f"{argv[0]} is not installed or not on PATH") from exc
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        tail = stderr.decode(errors="replace").strip().splitlines()[-5:]
        raise ProviderError(f"{argv[0]} failed: " + " | ".join(tail))
    return stdout.decode(errors="replace")


async def probe_duration(ffprobe_bin: str, path: Path) -> float:
    out = await run_process(
        ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    )  # fmt: skip
    try:
        return float(out.strip())
    except ValueError as exc:
        raise ProviderError(f"could not read duration of {path.name}") from exc
