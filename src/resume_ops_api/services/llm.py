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

        import sys
        is_testing = "pytest" in sys.modules
        max_attempts = 10
        min_wait = 0 if is_testing else 3
        max_wait = 0 if is_testing else 30

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=3, min=min_wait, max=max_wait),
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
            
            # Clean up potential markdown formatting code blocks or leading/trailing conversational text
            content_str = content.strip()
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", content_str, re.DOTALL)
            if match:
                content_str = match.group(1).strip()
            else:
                first_idx = min(
                    [idx for idx in [content_str.find("{"), content_str.find("[")] if idx != -1],
                    default=-1
                )
                last_idx = max(
                    [idx for idx in [content_str.rfind("}"), content_str.rfind("]")] if idx != -1],
                    default=-1
                )
                if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
                    content_str = content_str[first_idx : last_idx + 1].strip()

            # If the content doesn't start with '{' or '[', but looks like a key-value or field definition, wrap it in braces
            if not content_str.startswith("{") and not content_str.startswith("["):
                if ":" in content_str:
                    content_str = "{" + content_str + "}"

            parsed = json.loads(content_str)
            # Normalize list and dict wrappers to match target model schema
            if isinstance(parsed, list):
                model_fields = list(response_model.model_fields.keys())
                if len(parsed) == 1 and not any(isinstance(item, list) for item in parsed):
                    first_item = parsed[0]
                    if isinstance(first_item, dict) and any(k in model_fields for k in first_item.keys()):
                        parsed = first_item
                
                if isinstance(parsed, list):
                    list_field = None
                    for field_name, field_info in response_model.model_fields.items():
                        from typing import get_origin
                        if get_origin(field_info.annotation) is list:
                            list_field = field_name
                            break
                    if list_field:
                        parsed = {list_field: parsed}
            elif isinstance(parsed, dict):
                model_fields = set(response_model.model_fields.keys())
                if not (set(parsed.keys()) & model_fields):
                    list_values = [v for v in parsed.values() if isinstance(v, list)]
                    if len(list_values) == 1:
                        for field_name, field_info in response_model.model_fields.items():
                            from typing import get_origin
                            if get_origin(field_info.annotation) is list:
                                parsed = {field_name: list_values[0]}
                                break

            return response_model.model_validate(parsed)
        except Exception as exc:
            import logging
            logging.error(f"Structured LLM generation failed for model '{model}': {exc}. Raw content was: {repr(locals().get('content'))}, content_str was: {repr(locals().get('content_str'))}")
            raise AppError(
                f"Structured LLM generation failed for model '{model}'.",
                code="llm_generation_failed",
                status_code=502,
                details={"model": model, "error": str(exc)},
            ) from exc

