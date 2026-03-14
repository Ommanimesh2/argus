"""
ARGUS Agents — OpenAI (GPT) LLM client.
"""
import asyncio
from typing import Any

from .. import config
from .base import LLMClient


class OpenAILLMClient(LLMClient):
    """OpenAI Chat Completions API."""

    def __init__(self) -> None:
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 2000,
        system: str | None = None,
    ) -> str:
        model = model or "gpt-4o"
        if system:
            messages = [{"role": "system", "content": system}] + list(messages)
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        if not response.choices or not response.choices[0].message.content:
            return ""
        return response.choices[0].message.content
