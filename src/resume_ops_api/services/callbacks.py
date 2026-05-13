from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class CallbackService:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(__name__)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
        reraise=True,
    )
    async def deliver(self, callback_url: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(callback_url, json=payload)
            response.raise_for_status()

