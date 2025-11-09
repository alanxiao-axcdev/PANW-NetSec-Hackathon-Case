"""AI engine coordination layer.

Provides simple interface for text generation and embedding operations,
managing the underlying AI provider and handling initialization.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from companion.ai_backend import AIProvider, MockProvider
from companion.config import load_config

if TYPE_CHECKING:
    from companion.models import Config

logger = logging.getLogger(__name__)

_provider: AIProvider | None = None
_initialized: bool = False


async def initialize_model() -> None:
    """Initialize AI model for inference.

    Loads the configured AI provider and prepares it for use.
    Safe to call multiple times - will skip if already initialized.

    Raises:
        RuntimeError: If model initialization fails
    """
    global _provider, _initialized

    if _initialized and _provider is not None:
        logger.debug("Model already initialized")
        return

    logger.info("Initializing AI model")

    config = load_config()
    _provider = _get_provider(config)

    try:
        await _provider.initialize()
        _initialized = True
        logger.info("Model initialized successfully: %s", _provider.provider_name)
    except Exception as e:
        logger.error("Failed to initialize model: %s", e)
        _provider = None
        _initialized = False
        msg = f"Model initialization failed: {e}"
        raise RuntimeError(msg) from e


def _get_provider(config: "Config") -> AIProvider:
    """Get AI provider based on configuration.

    Args:
        config: Application configuration

    Returns:
        Configured AI provider instance

    Raises:
        ValueError: If provider name is not recognized
        RuntimeError: If provider initialization fails
    """
    from companion.ai_backend.qwen_provider import QwenProvider
    from companion.ai_backend.ollama_provider import OllamaProvider

    # Default to qwen for real AI experience
    provider_name = getattr(config, "ai_provider", "qwen")

    if provider_name == "qwen":
        logger.info("Initializing Qwen AI provider")
        # Let initialization errors propagate - no silent fallback
        return QwenProvider(model_name=config.model_name)
    elif provider_name == "ollama":
        logger.info("Initializing Ollama AI provider")
        # Let initialization errors propagate - no silent fallback
        return OllamaProvider()
    elif provider_name == "mock":
        logger.info("Using mock AI provider (testing mode)")
        return MockProvider()

    # Unrecognized provider - fail loudly with clear message
    msg = f"Unknown AI provider: {provider_name}. Valid options: qwen, ollama, mock"
    logger.error(msg)
    raise ValueError(msg)


async def generate_text(prompt: str, max_tokens: int = 200) -> str:
    """Generate text completion from prompt.

    Automatically initializes model if needed.

    Args:
        prompt: Input text prompt
        max_tokens: Maximum tokens to generate (default: 200)

    Returns:
        Generated text response

    Raises:
        ValueError: If prompt is empty
        RuntimeError: If generation fails
    """
    if not prompt or not prompt.strip():
        msg = "Prompt cannot be empty"
        raise ValueError(msg)

    if not _initialized or _provider is None:
        await initialize_model()

    if _provider is None:
        msg = "Provider not initialized"
        raise RuntimeError(msg)

    import time

    start_time = time.time()

    try:
        result = await _provider.generate(prompt, max_tokens=max_tokens)

        # Record metrics
        duration_ms = (time.time() - start_time) * 1000
        try:
            from companion.monitoring import metrics
            metrics.record_inference_time(duration_ms)
        except Exception as e:
            logger.debug("Metrics recording failed: %s", e)

        logger.debug("Generated %d chars from prompt in %.1fms", len(result), duration_ms)
        return result
    except Exception as e:
        logger.error("Text generation failed: %s", e)
        msg = f"Generation failed: {e}"
        raise RuntimeError(msg) from e


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text.

    Automatically initializes model if needed.

    Args:
        text: Input text to embed

    Returns:
        Embedding vector as list of floats

    Raises:
        ValueError: If text is empty
        RuntimeError: If embedding fails
    """
    if not text or not text.strip():
        msg = "Text cannot be empty"
        raise ValueError(msg)

    if not _initialized or _provider is None:
        await initialize_model()

    if _provider is None:
        msg = "Provider not initialized"
        raise RuntimeError(msg)

    try:
        embedding = await _provider.embed(text)
        logger.debug("Generated embedding of size %d", len(embedding))
        return embedding
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        msg = f"Embedding failed: {e}"
        raise RuntimeError(msg) from e


def ensure_model_downloaded() -> bool:
    """Check if model is available locally.

    For mock provider, always returns True since no model is needed.
    For real providers, would check if model files exist.

    Returns:
        True if model is available, False otherwise
    """
    if _provider is None or isinstance(_provider, MockProvider):
        return True

    logger.warning("Model download check not implemented for provider: %s", _provider.provider_name)
    return True


def is_initialized() -> bool:
    """Check if AI engine is initialized.

    Returns:
        True if initialized and ready for inference
    """
    return _initialized and _provider is not None


def get_provider_health() -> dict[str, str | bool | float | None]:
    """Get current AI provider health status.

    Returns detailed information about the active provider including
    initialization status, model details, and recent errors.

    Returns:
        Dict with health information:
        {
            "provider_name": str,
            "initialized": bool,
            "model_loaded": bool,
            "error": str | None,
            "last_inference_time_ms": float | None
        }
    """
    if _provider is None:
        return {
            "provider_name": "None",
            "initialized": False,
            "model_loaded": False,
            "error": "No provider initialized",
            "last_inference_time_ms": None,
        }

    health = _provider.get_health()
    return {
        "provider_name": health.provider_name,
        "initialized": health.is_initialized,
        "model_loaded": health.model_loaded,
        "error": None if health.error_count == 0 else f"{health.error_count} recent errors",
        "last_inference_time_ms": health.last_inference_time,
    }


async def shutdown() -> None:
    """Shutdown AI engine and cleanup resources."""
    global _provider, _initialized

    if _provider is not None:
        logger.info("Shutting down AI engine")
        await _provider.shutdown()

    _provider = None
    _initialized = False


def run_async(coro):
    """Helper to run async function in sync context.

    Args:
        coro: Coroutine to run

    Returns:
        Result of coroutine execution
    """
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro)
        return loop.run_until_complete(task)
    except RuntimeError:
        return asyncio.run(coro)
