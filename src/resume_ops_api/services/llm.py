from __future__ import annotations

import json
from typing import Any, TypeVar

import instructor
from litellm import acompletion
from pydantic import BaseModel

from resume_ops_api.core.exceptions import AppError

ModelT = TypeVar("ModelT", bound=BaseModel)


class StructuredLLMClient:
    def __init__(self, completion_fn: Any | None = None) -> None:
        self.completion_fn = completion_fn or acompletion

    async def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        try:
            client = instructor.from_litellm(self.completion_fn)
            response = await client.chat.completions.create(
                model=model,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            if isinstance(response, response_model):
                return response
        except Exception:
            pass

        try:
            completion = await self.completion_fn(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = completion["choices"][0]["message"]["content"]
            return response_model.model_validate(json.loads(content))
        except Exception as exc:
            raise AppError(
                f"Structured LLM generation failed for model '{model}'.",
                code="llm_generation_failed",
                status_code=502,
                details={"model": model, "error": str(exc)},
            ) from exc

