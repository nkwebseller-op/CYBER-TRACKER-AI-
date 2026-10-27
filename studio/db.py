from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .models import Job, JobRequest, JobStatus, Script

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    brief TEXT NOT NULL,
    tone TEXT NOT NULL,
    aspect TEXT NOT NULL,
    duration_s INTEGER NOT NULL,
    voice TEXT,
    script_json TEXT,
    error TEXT
)
"""


class JobStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, job_id: str, request: JobRequest) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO jobs (id, created_at, status, brief, tone, aspect, duration_s,"
                " voice, script_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    JobStatus.QUEUED.value,
                    request.brief,
                    request.tone,
                    request.aspect.value,
                    request.duration_s,
                    request.voice,
                    request.script.model_dump_json() if request.script else None,
                ),
            )

    def update(
        self, job_id: str, *, status: JobStatus, script: Script | None = None, error: str | None = None
    ) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE jobs SET status = ?, script_json = COALESCE(?, script_json), error = ?"
                " WHERE id = ?",
                (status.value, script.model_dump_json() if script else None, error, job_id),
            )

    def get(self, job_id: str) -> sqlite3.Row | None:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def list(self, limit: int = 50) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()

    def delete(self, job_id: str) -> bool:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,)).rowcount > 0

    def count_today(self) -> int:
        today = datetime.now(UTC).date().isoformat()
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE created_at >= ?", (today,)
            ).fetchone()
            return int(row["n"])

    def fail_interrupted(self) -> None:
        """Jobs left mid-flight by a previous process can never finish; mark them failed."""
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE jobs SET status = ?, error = ? WHERE status NOT IN (?, ?)",
                (
                    JobStatus.FAILED.value,
                    "Interrupted by server restart",
                    JobStatus.DONE.value,
                    JobStatus.FAILED.value,
                ),
            )


def row_to_job(row: sqlite3.Row, media_dir: Path) -> Job:
    job_dir = media_dir / row["id"]
    return Job(
        id=row["id"],
        created_at=row["created_at"],
        status=JobStatus(row["status"]),
        brief=row["brief"],
        tone=row["tone"],
        aspect=row["aspect"],
        duration_s=row["duration_s"],
        voice=row["voice"],
        script=Script.model_validate_json(row["script_json"]) if row["script_json"] else None,
        error=row["error"],
        video_url=f"/media/{row['id']}/video.mp4" if (job_dir / "video.mp4").exists() else None,
        audio_url=f"/media/{row['id']}/voice" if list(job_dir.glob("voice.*")) else None,
    )
