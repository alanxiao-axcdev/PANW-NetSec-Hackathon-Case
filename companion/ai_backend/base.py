"""Abstract base class for AI providers.

Defines the interface that all AI providers must implement for consistency
across different backends (local models, API services, mocks).
"""

import logging
from abc import ABC, abstractmethod

from companion.models import ProviderHealth

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI inference providers.

    All AI providers must implement this interface to ensure consistent
    behavior across different backends. Supports both text generation
    and embedding operations.

    Attributes:
        provider_name: Human-readable name of the provider
        is_initialized: Whether provider has been initialized
        error_count: Count of errors since last successful operation
    """

    def __init__(self, provider_name: str) -> None:
        """Initialize provider with name.

        Args:
            provider_name: Human-readable name for this provider
        """
        self.provider_name = provider_name
        self.is_initialized = False
        self.error_count = 0

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider and load necessary resources.

        This method should:
        - Load models into memory
        - Establish API connections
        - Validate credentials
        - Set is_initialized=True on success

        Raises:
            RuntimeError: If initialization fails
        """

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate text completion from prompt.

        Args:
            prompt: Input text to generate from
            max_tokens: Maximum tokens to generate (default: 100)

        Returns:
            Generated text completion

        Raises:
            RuntimeError: If generation fails
            ValueError: If prompt is empty or invalid
        """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            RuntimeError: If embedding fails
            ValueError: If text is empty
        """

    @abstractmethod
    def get_health(self) -> ProviderHealth:
        """Get current health status of provider.

        Returns:
            ProviderHealth object with status information
        """

    async def shutdown(self) -> None:
        """Clean up resources before shutdown.

        Optional cleanup method that providers can override to
        release resources gracefully.
        """
        self.is_initialized = False
        logger.info("Provider %s shut down", self.provider_name)
