from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator

from resume_ops_api.core.exceptions import ResumeValidationError


class ResumeSchemaValidator:
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft7Validator(self.schema)

    def validate(self, payload: dict, *, context: str, status_code: int = 422) -> None:
        errors = sorted(self.validator.iter_errors(payload), key=lambda item: list(item.path))
        if not errors:
            return
        details = {
            "context": context,
            "errors": [
                {
                    "path": ".".join(str(part) for part in error.path) or "$",
                    "message": error.message,
                }
                for error in errors
            ],
        }
        raise ResumeValidationError(
            f"The {context} failed JSON Resume schema validation.",
            details=details,
            status_code=status_code,
        )

