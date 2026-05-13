from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field


class TailorRequest(BaseModel):
    resume: dict[str, Any]
    job_description: str = Field(min_length=1)
    theme: str | None = None
    callback_url: AnyHttpUrl | None = None


class TailorResponse(BaseModel):
    resume: dict[str, Any]
    pdf_base64: str
    theme: str


class QueuedTaskResponse(BaseModel):
    task_id: str
    status: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class TaskError(BaseModel):
    code: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    resume: dict[str, Any] | None = None
    pdf_base64: str | None = None
    error: TaskError | None = None
    theme: str


class ThemeListResponse(BaseModel):
    default_theme: str
    allowed_themes: list[str]


class HealthResponse(BaseModel):
    status: str

