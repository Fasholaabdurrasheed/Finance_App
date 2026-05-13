from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.import_job import ImportJob


class ImportJobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, upload_id: int, message: str | None = None) -> ImportJob:
        job = ImportJob(
            upload_id=upload_id,
            status="queued",
            progress=0,
            logs=message,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def mark_running(self, job: ImportJob, message: str | None = None) -> ImportJob:
        job.status = "processing"
        job.progress = max(job.progress, 1)
        job.started_at = job.started_at or datetime.now(timezone.utc)
        if message:
            job.logs = self._append_log(job.logs, message)
        self.db.add(job)
        self.db.flush()
        return job

    def mark_complete(self, job: ImportJob, message: str | None = None) -> ImportJob:
        job.status = "complete"
        job.progress = 100
        job.finished_at = datetime.now(timezone.utc)
        if message:
            job.logs = self._append_log(job.logs, message)
        self.db.add(job)
        self.db.flush()
        return job

    def mark_failed(self, job: ImportJob, error: str) -> ImportJob:
        job.status = "failed"
        job.error = error
        job.finished_at = datetime.now(timezone.utc)
        job.logs = self._append_log(job.logs, error)
        self.db.add(job)
        self.db.flush()
        return job

    def append_log(self, job: ImportJob, message: str) -> ImportJob:
        job.logs = self._append_log(job.logs, message)
        self.db.add(job)
        self.db.flush()
        return job

    def _append_log(self, existing: str | None, message: str) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {message}"
        if not existing:
            return entry
        return f"{existing}\n{entry}"
