from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resume_ops_api.core.exceptions import AppError
from resume_ops_api.db.models import Base, Job, JobStatus
from resume_ops_api.db.session import Database
from resume_ops_api.services.store import JobStore


# ---------------------------------------------------------------------------
# Job model tests
# ---------------------------------------------------------------------------


class TestJobModel:
    """Tests for the Job SQLAlchemy model."""

    @pytest.fixture
    def sample_payload(self) -> dict:
        return {
            "resume": {"basics": {"name": "Test User", "email": "test@example.com"}},
            "job_description": "A job description for testing.",
        }

    def test_job_creation_defaults(self, sample_payload: dict) -> None:
        """Job can be instantiated with required fields.

        Note: SQLAlchemy column defaults (created_at / updated_at) are only
        applied by the *database server* on INSERT.  When just constructing
        a Python instance they remain None until the session flushes.
        """
        job = Job(
            id="test-job-1",
            status=JobStatus.QUEUED.value,
            request_payload=sample_payload,
            theme="jsonresume-theme-stackoverflow",
        )

        assert job.id == "test-job-1"
        assert job.status == JobStatus.QUEUED.value
        assert job.request_payload == sample_payload
        assert job.theme == "jsonresume-theme-stackoverflow"
        assert job.callback_url is None
        assert job.result_resume_json is None
        assert job.result_pdf_path is None
        assert job.error_code is None
        assert job.error_message is None
        # created_at / updated_at Python-side defaults are only applied
        # during INSERT (session flush), so they are None for bare instances
        assert job.created_at is None
        assert job.updated_at is None

    def test_job_creation_with_callback_url(self, sample_payload: dict) -> None:
        job = Job(
            id="test-job-2",
            status=JobStatus.QUEUED.value,
            request_payload=sample_payload,
            theme="jsonresume-theme-even",
            callback_url="https://hooks.example.com/notify",
        )
        assert job.callback_url == "https://hooks.example.com/notify"

    def test_job_creation_with_result_fields(self, sample_payload: dict) -> None:
        job = Job(
            id="test-job-3",
            status=JobStatus.COMPLETED.value,
            request_payload=sample_payload,
            theme="jsonresume-theme-stackoverflow",
            result_resume_json={"basics": {"name": "Tailored"}},
            result_pdf_path="/data/jobs/test-job-3/output.pdf",
        )
        assert job.result_resume_json == {"basics": {"name": "Tailored"}}
        assert job.result_pdf_path == "/data/jobs/test-job-3/output.pdf"

    def test_job_creation_with_error_fields(self, sample_payload: dict) -> None:
        job = Job(
            id="test-job-4",
            status=JobStatus.FAILED.value,
            request_payload=sample_payload,
            theme="jsonresume-theme-stackoverflow",
            error_code="render_failed",
            error_message="PDF rendering failed due to missing binary.",
        )
        assert job.error_code == "render_failed"
        assert job.error_message == "PDF rendering failed due to missing binary."

    def test_job_tablename_is_jobs(self) -> None:
        assert Job.__tablename__ == "jobs"

    def test_job_is_declarative_base_subclass(self) -> None:
        assert issubclass(Job, Base)


class TestJobStatusEnum:
    """Tests for the JobStatus StrEnum."""

    def test_job_status_values(self) -> None:
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_job_status_is_str_enum(self) -> None:
        assert issubclass(JobStatus, str)

    def test_job_status_members_count(self) -> None:
        assert len(JobStatus) == 4


# ---------------------------------------------------------------------------
# Database / JobStore integration tests (in-memory SQLite)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def database(tmp_path) -> Database:
    """Fixture providing an in-memory SQLite database, bootstrapped."""
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await db.bootstrap()
    return db


@pytest_asyncio.fixture
async def job_store(database: Database) -> JobStore:
    return JobStore(database)


class TestJobStore:
    """Integration tests for JobStore backed by a real SQLite database."""

    _SAMPLE_PAYLOAD = {
        "resume": {"basics": {"name": "Test User"}},
        "job_description": "Test JD",
    }

    @pytest.mark.asyncio
    async def test_create_and_get_job(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="create-get-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        job = await job_store.get("create-get-1")
        assert job is not None
        assert job.id == "create-get-1"
        assert job.status == JobStatus.QUEUED.value
        assert job.theme == "jsonresume-theme-stackoverflow"
        assert job.request_payload == self._SAMPLE_PAYLOAD
        assert job.callback_url is None

    @pytest.mark.asyncio
    async def test_create_job_with_callback_url(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="create-cb-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-even",
            callback_url="https://example.com/hook",
        )
        job = await job_store.get("create-cb-1")
        assert job is not None
        assert job.callback_url == "https://example.com/hook"

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_returns_none(self, job_store: JobStore) -> None:
        job = await job_store.get("nonexistent-job-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_or_raise_returns_job(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="gor-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        job = await job_store.get_or_raise("gor-1")
        assert job.id == "gor-1"

    @pytest.mark.asyncio
    async def test_get_or_raise_raises_for_missing_job(self, job_store: JobStore) -> None:
        with pytest.raises(AppError) as exc_info:
            await job_store.get_or_raise("missing-job")
        assert exc_info.value.code == "task_not_found"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_claim_next_queued_claims_a_job(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="claim-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        claimed = await job_store.claim_next_queued()
        assert claimed is not None
        assert claimed.id == "claim-1"
        assert claimed.status == JobStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_claim_next_queued_returns_none_when_empty(self, job_store: JobStore) -> None:
        claimed = await job_store.claim_next_queued()
        assert claimed is None

    @pytest.mark.asyncio
    async def test_claim_next_queued_returns_none_when_all_claimed(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="claim-empty-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        _ = await job_store.claim_next_queued()
        second = await job_store.claim_next_queued()
        assert second is None

    @pytest.mark.asyncio
    async def test_claim_next_queued_claims_in_fifo_order(self, job_store: JobStore) -> None:
        # Create two jobs
        await job_store.create(
            job_id="fifo-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        # Brief pause ensures different created_at timestamps
        import asyncio
        await asyncio.sleep(0.01)
        await job_store.create(
            job_id="fifo-2",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        first = await job_store.claim_next_queued()
        second = await job_store.claim_next_queued()
        assert first is not None
        assert second is not None
        assert first.id == "fifo-1"
        assert second.id == "fifo-2"

    @pytest.mark.asyncio
    async def test_requeue_running_sets_back_to_queued(self, job_store: JobStore) -> None:
        import asyncio
        await job_store.create(
            job_id="requeue-test",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        # Manually set to RUNNING via the database to simulate a crashed worker
        claimed = await job_store.claim_next_queued()
        assert claimed is not None
        assert claimed.status == JobStatus.RUNNING.value

        await job_store.requeue_running()

        job = await job_store.get("requeue-test")
        assert job is not None
        assert job.status == JobStatus.QUEUED.value

    @pytest.mark.asyncio
    async def test_mark_completed_sets_result_fields(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="complete-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        # Claim it first to simulate running
        _ = await job_store.claim_next_queued()

        result_resume = {"basics": {"name": "Tailored User"}}
        result_pdf_path = "/data/jobs/complete-1/output.pdf"
        await job_store.mark_completed(
            job_id="complete-1",
            resume=result_resume,
            pdf_path=result_pdf_path,
        )

        job = await job_store.get("complete-1")
        assert job is not None
        assert job.status == JobStatus.COMPLETED.value
        assert job.result_resume_json == result_resume
        assert job.result_pdf_path == result_pdf_path
        assert job.error_code is None
        assert job.error_message is None

    @pytest.mark.asyncio
    async def test_mark_failed_sets_error_fields(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="fail-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        _ = await job_store.claim_next_queued()

        await job_store.mark_failed(
            job_id="fail-1",
            error_code="llm_generation_failed",
            error_message="Structured LLM generation failed for model 'openai/gpt-4o-mini'.",
        )

        job = await job_store.get("fail-1")
        assert job is not None
        assert job.status == JobStatus.FAILED.value
        assert job.error_code == "llm_generation_failed"
        assert job.error_message == "Structured LLM generation failed for model 'openai/gpt-4o-mini'."

    @pytest.mark.asyncio
    async def test_updated_at_changes_on_status_transition(self, job_store: JobStore) -> None:
        await job_store.create(
            job_id="transition-1",
            payload=self._SAMPLE_PAYLOAD,
            theme="jsonresume-theme-stackoverflow",
            callback_url=None,
        )
        original = await job_store.get("transition-1")
        assert original is not None
        original_updated_at = original.updated_at

        # Small delay to ensure timestamp differs
        import asyncio
        await asyncio.sleep(0.01)

        claimed = await job_store.claim_next_queued()
        assert claimed is not None
        # updated_at should have been bumped by the claim operation
        assert claimed.updated_at != original_updated_at
