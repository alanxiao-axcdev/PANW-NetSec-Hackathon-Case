"""Ollama API provider.

Provides AI inference using Ollama REST API for local model serving.
Requires Ollama to be running separately.
"""

import logging
import time

import httpx

from companion.ai_backend.base import AIProvider
from companion.models import ProviderHealth
from companion.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """Ollama REST API provider.

    Connects to locally running Ollama service for model inference.
    Ollama must be installed and running separately.

    Attributes:
        base_url: Ollama API endpoint
        model_name: Model name in Ollama
        timeout: Request timeout in seconds
        client: HTTP client for API calls
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:1.5b",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model_name: Ollama model name (default: qwen2.5:1.5b)
            base_url: Ollama API URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 30.0)
        """
        super().__init__("OllamaProvider")
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client: httpx.AsyncClient | None = None
        self.last_inference_time: float | None = None

    async def initialize(self) -> None:
        """Initialize Ollama client and verify connection.

        Raises:
            RuntimeError: If Ollama is not reachable
        """
        if self.is_initialized:
            return

        try:
            self.client = httpx.AsyncClient(timeout=self.timeout)

            # Test connection
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()

            self.is_initialized = True
            logger.info("OllamaProvider initialized at %s", self.base_url)

        except Exception as e:
            logger.error("Failed to initialize OllamaProvider: %s", e)
            msg = f"Ollama not reachable at {self.base_url}: {e}"
            raise RuntimeError(msg) from e

    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate text using Ollama API.

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

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            }

            assert self.client is not None
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "")

            self.last_inference_time = (time.perf_counter() - start_time) * 1000
            logger.debug("Generated via Ollama in %.2fms", self.last_inference_time)

            return generated_text

        try:
            result = await retry_with_backoff(_generate, max_retries=2)
            self.error_count = 0
            return result
        except Exception as e:
            self.error_count += 1
            logger.error("Ollama generation failed: %s", e)
            msg = f"Ollama generation failed: {e}"
            raise RuntimeError(msg) from e

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using Ollama API.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector

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
            payload = {"model": self.model_name, "prompt": text}

            assert self.client is not None
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            embedding: list[float] = result.get("embedding", [])

            return embedding

        try:
            return await retry_with_backoff(_embed, max_retries=2)
        except Exception as e:
            self.error_count += 1
            logger.error("Ollama embedding failed: %s", e)
            msg = f"Ollama embedding failed: {e}"
            raise RuntimeError(msg) from e

    def get_health(self) -> ProviderHealth:
        """Get Ollama provider health status.

        Returns:
            ProviderHealth with current status
        """
        return ProviderHealth(
            provider_name=self.provider_name,
            is_initialized=self.is_initialized,
            model_loaded=self.is_initialized,  # Assume loaded if connected
            last_inference_time=self.last_inference_time,
            error_count=self.error_count,
        )

    async def shutdown(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        await super().shutdown()
