"""
ARGUS Agents — Claude (Anthropic) LLM client.
"""
import asyncio
from typing import Any

from .. import config
from .base import LLMClient


class ClaudeLLMClient(LLMClient):
    """Anthropic Claude via API."""

    def __init__(self) -> None:
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 2000,
        system: str | None = None,
    ) -> str:
        model = model or "claude-sonnet-4-20250514"
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = await asyncio.to_thread(
            self.client.messages.create,
            **kwargs,
        )
        if not response.content or not response.content[0].text:
            return ""
        return response.content[0].text
