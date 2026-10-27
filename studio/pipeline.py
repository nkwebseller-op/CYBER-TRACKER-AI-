from __future__ import annotations

import asyncio
import logging

from .config import Settings
from .db import JobStore
from .models import JobRequest, JobStatus
from .providers import Providers
from .providers.base import ProviderError

log = logging.getLogger("studio.pipeline")


class Pipeline:
    def __init__(self, settings: Settings, store: JobStore, providers: Providers) -> None:
        self._settings = settings
        self._store = store
        self._providers = providers
        self._slots = asyncio.Semaphore(settings.max_concurrent_jobs)
        self._tasks: set[asyncio.Task[None]] = set()

    def submit(self, job_id: str, request: JobRequest) -> None:
        task = asyncio.create_task(self._run(job_id, request))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        """Wait for in-flight jobs (used by tests and graceful shutdown)."""
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(self, job_id: str, request: JobRequest) -> None:
        async with self._slots:
            try:
                await self._execute(job_id, request)
            except ProviderError as exc:
                log.warning("job %s failed: %s", job_id, exc)
                self._store.update(job_id, status=JobStatus.FAILED, error=str(exc))
            except Exception:
                # Never leak internals to the client; the traceback goes to the server log.
                log.exception("job %s crashed", job_id)
                self._store.update(job_id, status=JobStatus.FAILED, error="Unexpected server error")

    async def _execute(self, job_id: str, request: JobRequest) -> None:
        job_dir = self._settings.media_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        script = request.script
        if script is None:
            self._store.update(job_id, status=JobStatus.SCRIPTING)
            script = await self._providers.script.write(
                request.brief, request.tone, request.duration_s
            )
        self._store.update(job_id, status=JobStatus.VOICING, script=script)
        voice_path = await self._providers.voice.synthesize(script.narration, job_dir, request.voice)

        self._store.update(job_id, status=JobStatus.RENDERING)
        await self._providers.video.render(script, voice_path, job_dir / "video.mp4", request.aspect)
        self._store.update(job_id, status=JobStatus.DONE)
