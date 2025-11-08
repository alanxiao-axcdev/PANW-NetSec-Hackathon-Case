"""Mock AI provider for testing.

Provides deterministic responses without requiring actual model inference.
Useful for unit tests and development when models aren't available.
"""

import logging

from companion.ai_backend.base import AIProvider
from companion.models import ProviderHealth

logger = logging.getLogger(__name__)


class MockProvider(AIProvider):
    """Mock provider returning hardcoded responses.

    For testing purposes only. Returns deterministic responses
    without any actual AI inference.

    Attributes:
        responses: Dictionary mapping prompts to responses
        embedding_dim: Dimension of embedding vectors (default: 384)
    """

    def __init__(self, embedding_dim: int = 384) -> None:
        """Initialize mock provider.

        Args:
            embedding_dim: Dimension of embedding vectors (default: 384)
        """
        super().__init__("MockProvider")
        self.embedding_dim = embedding_dim
        self.responses: dict[str, str] = {
            "generate_prompt": "What would you like to reflect on today?",
            "analyze_sentiment": "positive",
            "extract_themes": "reflection, gratitude",
            "generate_summary": "You've been focusing on personal growth.",
        }
        self.last_inference_time = 0.0

    async def initialize(self) -> None:
        """Initialize mock provider (instant)."""
        self.is_initialized = True
        logger.info("MockProvider initialized")

    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate mock text response.

        Args:
            prompt: Input prompt (used to select response)
            max_tokens: Ignored for mock provider

        Returns:
            Hardcoded mock response based on prompt content

        Raises:
            ValueError: If prompt is empty
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        # Return appropriate mock response based on prompt keywords
        if "prompt" in prompt.lower() or "reflect" in prompt.lower():
            response = self.responses["generate_prompt"]
        elif "sentiment" in prompt.lower() or "emotion" in prompt.lower():
            response = self.responses["analyze_sentiment"]
        elif "theme" in prompt.lower() or "topic" in prompt.lower():
            response = self.responses["extract_themes"]
        elif "summary" in prompt.lower():
            response = self.responses["generate_summary"]
        else:
            response = "Mock response for testing purposes"

        self.last_inference_time = 1.0  # Simulate 1ms inference
        logger.debug("MockProvider generated: %s", response[:50])
        return response

    async def embed(self, text: str) -> list[float]:
        """Generate mock embedding vector.

        Args:
            text: Input text (length affects embedding)

        Returns:
            Mock embedding vector based on text length

        Raises:
            ValueError: If text is empty
        """
        if not text:
            raise ValueError("Text cannot be empty")

        # Generate deterministic embedding based on text length
        # Use simple hash-based approach for consistency
        text_hash = sum(ord(c) for c in text[:100])
        embedding = [float((text_hash + i) % 100) / 100.0 for i in range(self.embedding_dim)]

        logger.debug("MockProvider embedded text of length %d", len(text))
        return embedding

    def get_health(self) -> ProviderHealth:
        """Get mock provider health status.

        Returns:
            ProviderHealth with mock status
        """
        return ProviderHealth(
            provider_name=self.provider_name,
            is_initialized=self.is_initialized,
            model_loaded=True,  # Mock always has "model" loaded
            last_inference_time=self.last_inference_time,
            error_count=self.error_count,
        )
