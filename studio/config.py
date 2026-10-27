from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


def _find_font() -> str:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return ""


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")))
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("FFPROBE_BIN", "ffprobe")
    font_file: str = os.getenv("FONT_FILE") or _find_font()

    script_provider: str = os.getenv("SCRIPT_PROVIDER", "template")
    voice_provider: str = os.getenv("VOICE_PROVIDER", "mock")
    video_provider: str = os.getenv("VIDEO_PROVIDER", "cards")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")

    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "")
    elevenlabs_model: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

    replicate_api_token: str = os.getenv("REPLICATE_API_TOKEN", "")
    replicate_video_model: str = os.getenv("REPLICATE_VIDEO_MODEL", "google/veo-3.1-fast")
    # JSON merged into every prediction input; model specific. Defaults suit the default model.
    replicate_video_input: str = os.getenv(
        "REPLICATE_VIDEO_INPUT", '{"generate_audio": false, "resolution": "720p"}'
    )
    replicate_clip_seconds: int = int(os.getenv("REPLICATE_CLIP_SECONDS", "8"))
    replicate_timeout_seconds: float = float(os.getenv("REPLICATE_TIMEOUT_SECONDS", "600"))
    replicate_max_clips: int = int(os.getenv("REPLICATE_MAX_CLIPS", "6"))

    # 0 means no cap: you are limited only by your provider keys and budget.
    max_jobs_per_day: int = int(os.getenv("MAX_JOBS_PER_DAY", "0"))
    max_concurrent_jobs: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))
    max_prompt_chars: int = int(os.getenv("MAX_PROMPT_CHARS", "4000"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "studio.sqlite3"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"
