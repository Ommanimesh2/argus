"""
ARGUS Agents — LLM abstraction (Claude + OpenAI).
Use get_llm() so pipeline nodes are provider-agnostic.
"""
from .base import LLMClient, get_llm

__all__ = ["LLMClient", "get_llm"]
