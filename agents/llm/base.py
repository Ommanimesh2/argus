"""
ARGUS Agents — LLM client interface and factory.
Pipeline nodes call get_llm().complete(messages, model=..., max_tokens=...) 
and work with either Claude or OpenAI.
"""
from abc import ABC, abstractmethod
from typing import Any

# Lazy factory: only load the selected provider
def get_llm() -> "LLMClient":
    from .. import config
    if config.LLM_PROVIDER == "openai":
        from .openai_client import OpenAILLMClient
        return OpenAILLMClient()
    from .claude_client import ClaudeLLMClient
    return ClaudeLLMClient()


class LLMClient(ABC):
    """Abstract LLM client: same interface for Claude and OpenAI."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 2000,
        system: str | None = None,
    ) -> str:
        """
        Send messages and return the assistant reply as text.
        messages: [{"role": "user"|"assistant"|"system", "content": "..."}, ...]
        model: optional override (e.g. fast vs deep model).
        system: optional system message (prepended for providers that support it).
        """
        pass
