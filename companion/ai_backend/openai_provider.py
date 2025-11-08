"""OpenAI API provider.

Provides AI inference using OpenAI's API. Useful for benchmarking
and as a fallback when local models are unavailable.
"""

import logging
import os
import time

from companion.ai_backend.base import AIProvider
from companion.models import ProviderHealth
from companion.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI API provider.

    Uses OpenAI's API for text generation and embeddings.
    Requires OPENAI_API_KEY environment variable.

    Attributes:
        model_name: OpenAI model name
        api_key: OpenAI API key
        client: OpenAI client instance
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            model_name: OpenAI model name (default: gpt-4o-mini)
            api_key: API key (default: from OPENAI_API_KEY env var)
        """
        super().__init__("OpenAIProvider")
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.last_inference_time: float | None = None

    async def initialize(self) -> None:
        """Initialize OpenAI client.

        Raises:
            RuntimeError: If API key is missing
        """
        if self.is_initialized:
            return

        if not self.api_key:
            msg = "OPENAI_API_KEY environment variable not set"
            raise RuntimeError(msg)

        try:
            # Import here to avoid dependency if not using this provider
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key)
            self.is_initialized = True
            logger.info("OpenAIProvider initialized with model %s", self.model_name)

        except Exception as e:
            logger.error("Failed to initialize OpenAIProvider: %s", e)
            msg = f"OpenAI initialization failed: {e}"
            raise RuntimeError(msg) from e

    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate text using OpenAI API.

        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate (default: 100)

        Returns:
            Generated text completion

        Raises:
            RuntimeError: If generation fails
            ValueError: If prompt is empty
        """
        if not prompt:
            msg = "Prompt cannot be empty"
            raise ValueError(msg)

        if not self.is_initialized or not self.client:
            await self.initialize()

        async def _generate() -> str:
            start_time = time.perf_counter()

            assert self.client is not None
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )

            generated_text = response.choices[0].message.content or ""

            self.last_inference_time = (time.perf_counter() - start_time) * 1000
            logger.debug("Generated via OpenAI in %.2fms", self.last_inference_time)

            return generated_text

        try:
            result = await retry_with_backoff(_generate, max_retries=2)
            self.error_count = 0
            return result
        except Exception as e:
            self.error_count += 1
            logger.error("OpenAI generation failed: %s", e)
            msg = f"OpenAI generation failed: {e}"
            raise RuntimeError(msg) from e

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)

        Raises:
            RuntimeError: If embedding fails
            ValueError: If text is empty
        """
        if not text:
            msg = "Text cannot be empty"
            raise ValueError(msg)

        if not self.is_initialized or not self.client:
            await self.initialize()

        async def _embed() -> list[float]:
            assert self.client is not None
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )

            embedding: list[float] = response.data[0].embedding
            return embedding

        try:
            return await retry_with_backoff(_embed, max_retries=2)
        except Exception as e:
            self.error_count += 1
            logger.error("OpenAI embedding failed: %s", e)
            msg = f"OpenAI embedding failed: {e}"
            raise RuntimeError(msg) from e

    def get_health(self) -> ProviderHealth:
        """Get OpenAI provider health status.

        Returns:
            ProviderHealth with current status
        """
        return ProviderHealth(
            provider_name=self.provider_name,
            is_initialized=self.is_initialized,
            model_loaded=self.is_initialized,  # API-based, always "loaded"
            last_inference_time=self.last_inference_time,
            error_count=self.error_count,
        )
