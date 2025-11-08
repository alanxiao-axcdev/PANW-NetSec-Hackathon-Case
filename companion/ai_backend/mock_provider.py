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
        """Generate mock text response with basic content analysis.

        Args:
            prompt: Input prompt (used to select response)
            max_tokens: Ignored for mock provider

        Returns:
            Mock response based on prompt content and entry text analysis

        Raises:
            ValueError: If prompt is empty
        """
        if not prompt:
            msg = "Prompt cannot be empty"
            raise ValueError(msg)

        prompt_lower = prompt.lower()

        # Sentiment analysis - actually analyze the text in the prompt
        if "sentiment" in prompt_lower:
            response = self._analyze_sentiment_from_prompt(prompt)
        # Theme extraction - detect themes from text
        elif "theme" in prompt_lower or "topic" in prompt_lower:
            response = self._extract_themes_from_prompt(prompt)
        # Prompt generation
        elif "prompt" in prompt_lower or "question" in prompt_lower or "reflect" in prompt_lower:
            response = self.responses["generate_prompt"]
        # Summary
        elif "summary" in prompt_lower:
            response = self.responses["generate_summary"]
        else:
            response = "Mock response for testing purposes"

        self.last_inference_time = 1.0  # Simulate 1ms inference
        logger.debug("MockProvider generated: %s", response[:50])
        return response

    def _analyze_sentiment_from_prompt(self, prompt: str) -> str:
        """Analyze sentiment based on keywords in the entry text.

        Extracts the journal entry from the prompt and does keyword matching.
        """
        # Common negative keywords
        negative_words = [
            "terrible", "awful", "bad", "hate", "angry", "sad", "frustrated",
            "disappointed", "upset", "depressed", "anxious", "stressed", "worried",
            "failed", "failure", "wrong", "horrible", "miserable"
        ]

        # Common positive keywords
        positive_words = [
            "great", "good", "happy", "excellent", "wonderful", "amazing",
            "fantastic", "excited", "joy", "love", "grateful", "thankful",
            "accomplished", "success", "proud", "breakthrough", "energized"
        ]

        prompt_lower = prompt.lower()

        # Count sentiment words
        neg_count = sum(1 for word in negative_words if word in prompt_lower)
        pos_count = sum(1 for word in positive_words if word in prompt_lower)

        # Determine sentiment
        if neg_count > pos_count and neg_count > 0:
            return "negative"
        elif pos_count > neg_count and pos_count > 0:
            return "positive"
        else:
            return "neutral"

    def _extract_themes_from_prompt(self, prompt: str) -> str:
        """Extract themes based on keywords in the entry text."""
        prompt_lower = prompt.lower()
        themes = []

        # Theme keywords
        if any(word in prompt_lower for word in ["work", "job", "project", "meeting", "deadline", "boss"]):
            themes.append("work")
        if any(word in prompt_lower for word in ["family", "mom", "dad", "sister", "brother", "parent"]):
            themes.append("relationships")
        if any(word in prompt_lower for word in ["exercise", "run", "gym", "health", "workout"]):
            themes.append("health")
        if any(word in prompt_lower for word in ["friend", "social", "party", "hangout"]):
            themes.append("social")
        if any(word in prompt_lower for word in ["stress", "anxiety", "worry", "pressure"]):
            themes.append("stress")
        if any(word in prompt_lower for word in ["grateful", "thankful", "appreciate", "blessing"]):
            themes.append("gratitude")
        if any(word in prompt_lower for word in ["learn", "study", "read", "course", "education"]):
            themes.append("learning")
        if any(word in prompt_lower for word in ["creative", "art", "music", "write", "create"]):
            themes.append("creativity")

        # Default if nothing detected
        if not themes:
            themes = ["personal", "reflection"]

        return ", ".join(themes)

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
            msg = "Text cannot be empty"
            raise ValueError(msg)

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
