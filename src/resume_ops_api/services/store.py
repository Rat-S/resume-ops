from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from resume_ops_api.core.exceptions import AppError
from resume_ops_api.db.models import Job, JobStatus
from resume_ops_api.db.session import Database


class JobStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create(self, *, job_id: str, payload: dict[str, Any], theme: str, callback_url: str | None) -> None:
        async with self.database.session() as session:
            session.add(
                Job(
                    id=job_id,
                    status=JobStatus.QUEUED.value,
                    request_payload=payload,
                    theme=theme,
                    callback_url=callback_url,
                )
            )
            await session.commit()

    async def get(self, job_id: str) -> Job | None:
        async with self.database.session() as session:
            return await session.get(Job, job_id)

    async def get_or_raise(self, job_id: str) -> Job:
        job = await self.get(job_id)
        if not job:
            raise AppError("Task not found.", code="task_not_found", status_code=404)
        return job

    async def claim_next_queued(self) -> Job | None:
        async with self.database.session() as session:
            result = await session.execute(
                select(Job).where(Job.status == JobStatus.QUEUED.value).order_by(Job.created_at.asc()).limit(1)
            )
            job = result.scalar_one_or_none()
            if not job:
                return None
            update_result = await session.execute(
                update(Job)
                .where(Job.id == job.id, Job.status == JobStatus.QUEUED.value)
                .values(status=JobStatus.RUNNING.value, updated_at=datetime.now(UTC))
            )
            if update_result.rowcount != 1:
                await session.rollback()
                return None
            await session.commit()
            return await session.get(Job, job.id)

    async def requeue_running(self) -> None:
        async with self.database.session() as session:
            await session.execute(
                update(Job)
                .where(Job.status == JobStatus.RUNNING.value)
                .values(status=JobStatus.QUEUED.value, updated_at=datetime.now(UTC))
            )
            await session.commit()

    async def mark_completed(self, *, job_id: str, resume: dict[str, Any], pdf_path: str) -> None:
        async with self.database.session() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status=JobStatus.COMPLETED.value,
                    result_resume_json=resume,
                    result_pdf_path=pdf_path,
                    error_code=None,
                    error_message=None,
                    updated_at=datetime.now(UTC),
                )
            )
            await session.commit()

    async def mark_failed(self, *, job_id: str, error_code: str, error_message: str) -> None:
        async with self.database.session() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status=JobStatus.FAILED.value,
                    error_code=error_code,
                    error_message=error_message,
                    updated_at=datetime.now(UTC),
                )
            )
            await session.commit()

