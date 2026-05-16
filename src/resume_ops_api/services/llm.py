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
        session_id: str | None = None,
    ) -> ModelT:
        extra_headers: dict[str, str] = {}
        if session_id:
            extra_headers["X-Session-Id"] = session_id

        # 1. First, try strict JSON Schema mode (OpenAI Structured Outputs)
        try:
            client = instructor.from_litellm(self.completion_fn, mode=instructor.Mode.JSON_OAI, max_retries=2)
            response = await client.chat.completions.create(
                model=model,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                extra_headers=extra_headers or None,
            )
            if isinstance(response, response_model):
                return response
        except Exception as e:
            import logging
            logging.debug(f"JSON_OAI strict mode failed for model '{model}': {e}. Falling back to tool calling.")

        # 2. Fall back to standard Tool Calling
        try:
            client = instructor.from_litellm(self.completion_fn, mode=instructor.Mode.TOOLS, max_retries=2)
            response = await client.chat.completions.create(
                model=model,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                extra_headers=extra_headers or None,
            )
            if isinstance(response, response_model):
                return response
        except Exception as e:
            import logging
            logging.debug(f"Tool calling mode failed for model '{model}': {e}. Falling back to raw JSON object mode.")

        # 3. Final fallback to raw acompletion with json_object
        try:
            completion = await self.completion_fn(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                extra_headers=extra_headers or None,
            )
            content = completion["choices"][0]["message"]["content"]
            return response_model.model_validate(json.loads(content))
        except Exception as exc:
            import logging
            logging.error(f"Structured LLM generation failed for model '{model}': {exc}")
            raise AppError(
                f"Structured LLM generation failed for model '{model}'.",
                code="llm_generation_failed",
                status_code=502,
                details={"model": model, "error": str(exc)},
            ) from exc

