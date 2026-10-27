from __future__ import annotations

import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import JobStore, row_to_job
from .models import Job, JobRequest, Script, Tone
from .pipeline import Pipeline
from .providers import ProviderError, build_providers

_STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    store = JobStore(settings.db_path)
    providers = build_providers(settings)
    pipeline = Pipeline(settings, store, providers)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.fail_interrupted()
        yield
        await pipeline.drain()

    app = FastAPI(title="Spotlight Studio", lifespan=lifespan)
    app.state.pipeline = pipeline

    def load(job_id: str) -> Job:
        row = store.get(job_id)
        if row is None:
            raise HTTPException(404, "Job not found")
        return row_to_job(row, settings.media_dir)

    @app.get("/api/config")
    def get_config() -> dict[str, object]:
        return {
            "voice_provider": settings.voice_provider,
            "video_provider": settings.video_provider,
            "max_jobs_per_day": settings.max_jobs_per_day or None,
            "jobs_today": store.count_today(),
        }

    @app.get("/api/voices")
    async def list_voices() -> list[dict[str, str]]:
        lister = getattr(providers.voice, "list_voices", None)
        if lister is None:
            return []
        try:
            return await lister()
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.post("/api/script", response_model=Script)
    async def preview_script(brief: str, tone: Tone = "energetic", duration_s: int = 20) -> Script:
        if not 3 <= len(brief) <= settings.max_prompt_chars:
            raise HTTPException(422, "Brief length is out of range")
        return await providers.script.write(brief, tone, max(5, min(duration_s, 120)))

    @app.post("/api/jobs", response_model=Job, status_code=202)
    async def create_job(request: JobRequest) -> Job:
        if len(request.brief) > settings.max_prompt_chars:
            raise HTTPException(422, f"Brief is longer than {settings.max_prompt_chars} characters")
        cap = settings.max_jobs_per_day
        if cap and store.count_today() >= cap:
            raise HTTPException(429, f"Daily limit of {cap} videos reached")
        job_id = uuid.uuid4().hex
        store.create(job_id, request)
        pipeline.submit(job_id, request)
        return load(job_id)

    @app.get("/api/jobs", response_model=list[Job])
    def list_jobs() -> list[Job]:
        return [row_to_job(r, settings.media_dir) for r in store.list()]

    @app.get("/api/jobs/{job_id}", response_model=Job)
    def get_job(job_id: str) -> Job:
        return load(job_id)

    @app.delete("/api/jobs/{job_id}", status_code=204, response_model=None)
    def delete_job(job_id: str) -> None:
        # uuid4().hex only: reject anything that could escape the media directory.
        if not _is_job_id(job_id) or not store.delete(job_id):
            raise HTTPException(404, "Job not found")
        shutil.rmtree(settings.media_dir / job_id, ignore_errors=True)

    @app.get("/media/{job_id}/video.mp4")
    def get_video(job_id: str) -> FileResponse:
        path = settings.media_dir / job_id / "video.mp4"
        if not _is_job_id(job_id) or not path.exists():
            raise HTTPException(404, "Video not found")
        return FileResponse(path, media_type="video/mp4")

    @app.get("/media/{job_id}/voice")
    def get_voice(job_id: str) -> FileResponse:
        matches = list((settings.media_dir / job_id).glob("voice.*")) if _is_job_id(job_id) else []
        if not matches:
            raise HTTPException(404, "Voiceover not found")
        return FileResponse(matches[0])

    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="static")
    return app


def _is_job_id(value: str) -> bool:
    return len(value) == 32 and all(c in "0123456789abcdef" for c in value)
