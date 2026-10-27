from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Aspect(StrEnum):
    VERTICAL = "9:16"
    SQUARE = "1:1"
    WIDE = "16:9"

    @property
    def size(self) -> tuple[int, int]:
        return {"9:16": (720, 1280), "1:1": (720, 720), "16:9": (1280, 720)}[self.value]


Tone = Literal["energetic", "professional", "friendly", "luxury"]


class Scene(BaseModel):
    caption: str
    narration: str


class Script(BaseModel):
    title: str
    scenes: list[Scene]

    @property
    def narration(self) -> str:
        return " ".join(scene.narration for scene in self.scenes)


class JobRequest(BaseModel):
    brief: str = Field(min_length=3)
    tone: Tone = "energetic"
    aspect: Aspect = Aspect.VERTICAL
    duration_s: int = Field(default=20, ge=5, le=120)
    voice: str | None = None
    # Optional hand-written script; skips the script-writing stage when set.
    script: Script | None = None


class JobStatus(StrEnum):
    QUEUED = "queued"
    SCRIPTING = "scripting"
    VOICING = "voicing"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    created_at: str
    status: JobStatus
    brief: str
    tone: str
    aspect: str
    duration_s: int
    voice: str | None = None
    script: Script | None = None
    error: str | None = None
    video_url: str | None = None
    audio_url: str | None = None
