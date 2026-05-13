from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ResumeValidationError(AppError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None, status_code: int = 422) -> None:
        super().__init__(
            message,
            code="resume_validation_failed",
            status_code=status_code,
            details=details,
        )

