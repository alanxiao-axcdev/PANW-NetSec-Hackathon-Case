"""Qwen local model provider.

Provides AI inference using Qwen2.5-1.5B model running locally
via HuggingFace transformers. Downloads model on first use.
"""

import logging
import time
from pathlib import Path

from companion.ai_backend.base import AIProvider
from companion.models import ProviderHealth
from companion.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class QwenProvider(AIProvider):
    """Qwen local inference provider.

    Uses HuggingFace transformers to run Qwen2.5-1.5B locally.
    Model is downloaded and cached on first use.

    Attributes:
        model_name: HuggingFace model identifier
        device: Compute device (cpu, cuda, mps)
        model: Loaded transformer model
        tokenizer: Model tokenizer
        cache_dir: Where models are cached
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-1.5B",
        device: str = "cpu",
        cache_dir: Path | None = None,
    ) -> None:
        """Initialize Qwen provider.

        Args:
            model_name: HuggingFace model ID (default: Qwen/Qwen2.5-1.5B)
            device: Compute device (default: cpu)
            cache_dir: Model cache directory (default: ~/.cache/huggingface)
        """
        super().__init__("QwenProvider")
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir or Path.home() / ".cache" / "huggingface"
        self.model = None
        self.tokenizer = None
        self.last_inference_time: float | None = None

    async def initialize(self) -> None:
        """Initialize Qwen provider and download model if needed.

        Downloads model on first use with progress indication.
        Subsequent runs load from cache instantly.

        Raises:
            RuntimeError: If model loading fails
        """
        if self.is_initialized:
            logger.info("QwenProvider already initialized")
            return

        try:
            # Import here to avoid dependency if not using this provider
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info("Loading Qwen model: %s", self.model_name)
            logger.info("This may take a while on first run (downloading model)...")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=str(self.cache_dir),
                trust_remote_code=True,
            )

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                cache_dir=str(self.cache_dir),
                trust_remote_code=True,
                torch_dtype="auto",
            )
            self.model.to(self.device)
            self.model.eval()

            self.is_initialized = True
            logger.info("QwenProvider initialized successfully on %s", self.device)

        except Exception as e:
            logger.error("Failed to initialize QwenProvider: %s", e)
            msg = f"Qwen initialization failed: {e}"
            raise RuntimeError(msg) from e

    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate text using Qwen model.

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

        if not self.is_initialized or not self.model or not self.tokenizer:
            await self.initialize()

        async def _generate() -> str:
            import torch

            start_time = time.perf_counter()

            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            # Decode output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Remove prompt from output (model includes it)
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt) :].strip()

            # Track inference time
            self.last_inference_time = (time.perf_counter() - start_time) * 1000
            logger.debug("Generated %d tokens in %.2fms", max_tokens, self.last_inference_time)

            return generated_text

        try:
            result = await retry_with_backoff(_generate, max_retries=2)
            self.error_count = 0  # Reset on success
            return result
        except Exception as e:
            self.error_count += 1
            logger.error("Generation failed: %s", e)
            msg = f"Qwen generation failed: {e}"
            raise RuntimeError(msg) from e

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using Qwen model's hidden states.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (384 dimensions)

        Raises:
            RuntimeError: If embedding fails
            ValueError: If text is empty
        """
        if not text:
            msg = "Text cannot be empty"
            raise ValueError(msg)

        if not self.is_initialized or not self.model or not self.tokenizer:
            await self.initialize()

        async def _embed() -> list[float]:
            import torch

            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(
                self.device
            )

            # Get hidden states
            with torch.no_grad():
                outputs = self.model(**inputs, output_hidden_states=True)
                # Use mean of last hidden state as embedding
                last_hidden = outputs.hidden_states[-1]

                # Convert from BFloat16 to Float32 if needed (compatibility)
                if last_hidden.dtype == torch.bfloat16:
                    last_hidden = last_hidden.float()

                embedding = last_hidden.mean(dim=1).squeeze()

                # Convert to list and normalize
                return embedding.cpu().numpy().tolist()


        try:
            return await retry_with_backoff(_embed, max_retries=2)
        except Exception as e:
            self.error_count += 1
            logger.error("Embedding failed: %s", e)
            msg = f"Qwen embedding failed: {e}"
            raise RuntimeError(msg) from e

    def get_health(self) -> ProviderHealth:
        """Get Qwen provider health status.

        Returns:
            ProviderHealth with current status
        """
        return ProviderHealth(
            provider_name=self.provider_name,
            is_initialized=self.is_initialized,
            model_loaded=self.model is not None,
            last_inference_time=self.last_inference_time,
            error_count=self.error_count,
        )
