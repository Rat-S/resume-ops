from __future__ import annotations

import json
from typing import Any, TypeVar, cast

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
        from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception
        import logging

        def should_retry(exc: Exception) -> bool:
            from pydantic import ValidationError
            # Check if the exception or its original cause is a Pydantic ValidationError
            if isinstance(exc, ValidationError) or isinstance(exc.__cause__, ValidationError):
                return False
            # Do not retry permanent client/auth errors (e.g. 400 Bad Request, 401 Unauthorized)
            exc_name = type(exc).__name__
            if exc_name in ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError"):
                return False
            
            logging.warning(f"Structured LLM client encountered error: {exc}. Retrying...")
            return True

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception(should_retry),
            reraise=True,
        ):
            with attempt:
                from typing import cast
                return await cast(
                    Any,
                    self._generate_structured_internal(
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                        session_id=session_id,
                    ),
                )

    async def _generate_structured_internal(
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
            client = cast(Any, instructor.from_litellm(self.completion_fn, mode=instructor.Mode.JSON_OAI, max_retries=2))
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
            client = cast(Any, instructor.from_litellm(self.completion_fn, mode=instructor.Mode.TOOLS, max_retries=2))
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
            
            # Clean up potential markdown formatting code blocks (e.g. ```json ... ```)
            content_str = content.strip()
            if content_str.startswith("```"):
                lines = content_str.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content_str = "\n".join(lines).strip()

            parsed = json.loads(content_str)
            # If the response is wrapped in a list, extract the dictionary
            if isinstance(parsed, list) and len(parsed) == 1:
                parsed = parsed[0]
            elif isinstance(parsed, list) and len(parsed) > 1:
                for item in parsed:
                    if isinstance(item, dict):
                        parsed = item
                        break

            return response_model.model_validate(parsed)
        except Exception as exc:
            import logging
            logging.error(f"Structured LLM generation failed for model '{model}': {exc}")
            raise AppError(
                f"Structured LLM generation failed for model '{model}'.",
                code="llm_generation_failed",
                status_code=502,
                details={"model": model, "error": str(exc)},
            ) from exc

