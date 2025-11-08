"""AI Backend Architecture.

Pluggable AI provider system supporting multiple inference backends.
"""

from companion.ai_backend.base import AIProvider
from companion.ai_backend.mock_provider import MockProvider
from companion.ai_backend.ollama_provider import OllamaProvider
from companion.ai_backend.openai_provider import OpenAIProvider
from companion.ai_backend.qwen_provider import QwenProvider

__all__ = [
    "AIProvider",
    "QwenProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "MockProvider",
]
