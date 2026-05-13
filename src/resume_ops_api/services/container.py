from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resume_ops_api.core.config import Settings
from resume_ops_api.db.session import Database
from resume_ops_api.graph.merge import ResumeMerger
from resume_ops_api.graph.pipeline import ResumeGraph
from resume_ops_api.services.callbacks import CallbackService
from resume_ops_api.services.jobs import AsyncJobRunner
from resume_ops_api.services.llm import StructuredLLMClient
from resume_ops_api.services.orchestrator import TailorOrchestrator
from resume_ops_api.services.renderer import ResumeRenderer
from resume_ops_api.services.schema import ResumeSchemaValidator
from resume_ops_api.services.store import JobStore
from resume_ops_api.services.themes import ThemeService


@dataclass
class ServiceContainer:
    settings: Settings
    database: Database
    validator: ResumeSchemaValidator
    theme_service: ThemeService
    llm_client: StructuredLLMClient
    renderer: ResumeRenderer
    callback_service: CallbackService
    job_store: JobStore
    orchestrator: TailorOrchestrator
    job_runner: AsyncJobRunner

    async def start(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.jobs_dir.mkdir(parents=True, exist_ok=True)
        await self.database.bootstrap()
        await self.job_runner.start()

    async def stop(self) -> None:
        await self.job_runner.stop()
        await self.database.dispose()


def build_container(settings: Settings, **overrides: Any) -> ServiceContainer:
    database = overrides.get("database") or Database(settings.resolved_database_url)
    validator = overrides.get("validator") or ResumeSchemaValidator(settings.schema_path)
    theme_service = overrides.get("theme_service") or ThemeService(settings.allowed_themes, settings.default_theme)
    llm_client = overrides.get("llm_client") or StructuredLLMClient()
    renderer = overrides.get("renderer") or ResumeRenderer()
    callback_service = overrides.get("callback_service") or CallbackService(settings.callback_timeout_seconds)
    merger = overrides.get("merger") or ResumeMerger()
    graph = overrides.get("graph") or ResumeGraph(
        llm_client=llm_client,
        merger=merger,
        renderer=renderer,
        validator=validator,
        strategy_model=settings.strategy_model,
        work_model=settings.work_model,
        education_model=settings.education_model,
        skills_model=settings.skills_model,
        projects_model=settings.projects_model,
        optional_sections_model=settings.optional_sections_model,
    )
    orchestrator = overrides.get("orchestrator") or TailorOrchestrator(
        graph=graph,
        validator=validator,
        jobs_dir=settings.jobs_dir,
    )
    job_store = overrides.get("job_store") or JobStore(database)
    job_runner = overrides.get("job_runner") or AsyncJobRunner(
        store=job_store,
        orchestrator=orchestrator,
        callback_service=callback_service,
        max_concurrency=settings.max_concurrent_jobs,
    )
    return ServiceContainer(
        settings=settings,
        database=database,
        validator=validator,
        theme_service=theme_service,
        llm_client=llm_client,
        renderer=renderer,
        callback_service=callback_service,
        job_store=job_store,
        orchestrator=orchestrator,
        job_runner=job_runner,
    )

