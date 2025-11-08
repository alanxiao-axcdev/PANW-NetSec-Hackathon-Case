"""Tests for AI backend providers."""

import pytest

from companion.ai_backend import AIProvider, MockProvider, OllamaProvider, OpenAIProvider, QwenProvider
from companion.models import ProviderHealth


class TestAIProviderInterface:
    """Test abstract AIProvider interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AIProvider("test")

    def test_subclass_must_implement_methods(self):
        """Subclasses must implement all abstract methods."""

        class IncompleteProvider(AIProvider):
            """Intentionally incomplete provider."""

            async def initialize(self) -> None:
                pass

        with pytest.raises(TypeError):
            IncompleteProvider("incomplete")


class TestMockProvider:
    """Test MockProvider for deterministic testing."""

    @pytest.fixture
    def provider(self):
        """Create mock provider."""
        return MockProvider(embedding_dim=384)

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        """Initialization succeeds instantly."""
        await provider.initialize()
        assert provider.is_initialized
        assert provider.provider_name == "MockProvider"

    @pytest.mark.asyncio
    async def test_generate_with_prompt_keyword(self, provider):
        """Generate returns appropriate mock response."""
        await provider.initialize()

        result = await provider.generate("Generate a reflection prompt")
        assert "reflect" in result.lower() or "prompt" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_with_sentiment_keyword(self, provider):
        """Generate detects sentiment keywords."""
        await provider.initialize()

        result = await provider.generate("Analyze sentiment of this text")
        assert "positive" in result.lower() or "sentiment" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_empty_prompt_raises(self, provider):
        """Empty prompt raises ValueError."""
        await provider.initialize()

        with pytest.raises(ValueError, match="cannot be empty"):
            await provider.generate("")

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimension(self, provider):
        """Embedding has correct dimension."""
        await provider.initialize()

        embedding = await provider.embed("Test text")
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_deterministic(self, provider):
        """Same text produces same embedding."""
        await provider.initialize()

        embedding1 = await provider.embed("Test text")
        embedding2 = await provider.embed("Test text")
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_empty_text_raises(self, provider):
        """Empty text raises ValueError."""
        await provider.initialize()

        with pytest.raises(ValueError, match="cannot be empty"):
            await provider.embed("")

    @pytest.mark.asyncio
    async def test_get_health(self, provider):
        """Health status reflects provider state."""
        # Before initialization
        health = provider.get_health()
        assert not health.is_initialized
        assert health.provider_name == "MockProvider"

        # After initialization
        await provider.initialize()
        health = provider.get_health()
        assert health.is_initialized
        assert health.model_loaded

    @pytest.mark.asyncio
    async def test_tracks_inference_time(self, provider):
        """Provider tracks last inference time."""
        await provider.initialize()

        await provider.generate("test prompt")
        health = provider.get_health()
        assert health.last_inference_time is not None
        assert health.last_inference_time > 0


class TestQwenProvider:
    """Test QwenProvider (requires transformers library)."""

    @pytest.fixture
    def provider(self):
        """Create Qwen provider."""
        return QwenProvider(model_name="Qwen/Qwen2.5-1.5B", device="cpu")

    def test_initialization_attributes(self, provider):
        """Provider has correct attributes before init."""
        assert provider.provider_name == "QwenProvider"
        assert not provider.is_initialized
        assert provider.model is None
        assert provider.tokenizer is None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_initialize_downloads_model(self, provider):
        """Initialize downloads and loads model (slow test)."""
        # Skip if transformers not available
        pytest.importorskip("transformers")

        await provider.initialize()
        assert provider.is_initialized
        assert provider.model is not None
        assert provider.tokenizer is not None

    @pytest.mark.asyncio
    async def test_generate_requires_initialization(self, provider):
        """Generate initializes provider if needed."""
        pytest.importorskip("transformers")

        # Should auto-initialize
        result = await provider.generate("Hello", max_tokens=10)
        assert provider.is_initialized
        assert isinstance(result, str)

    def test_get_health_before_init(self, provider):
        """Health status works before initialization."""
        health = provider.get_health()
        assert health.provider_name == "QwenProvider"
        assert not health.is_initialized
        assert not health.model_loaded


class TestOllamaProvider:
    """Test OllamaProvider (requires Ollama running)."""

    @pytest.fixture
    def provider(self):
        """Create Ollama provider."""
        return OllamaProvider(model_name="qwen2.5:1.5b", base_url="http://localhost:11434")

    def test_initialization_attributes(self, provider):
        """Provider has correct attributes."""
        assert provider.provider_name == "OllamaProvider"
        assert not provider.is_initialized
        assert provider.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_initialize_requires_ollama_running(self, provider):
        """Initialize fails if Ollama not running."""
        # This will fail unless Ollama is actually running
        with pytest.raises(RuntimeError, match="not reachable"):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_closes_client(self, provider):
        """Shutdown closes HTTP client."""
        provider.is_initialized = True
        # Create mock client
        import httpx

        provider.client = httpx.AsyncClient()

        await provider.shutdown()
        assert not provider.is_initialized


class TestOpenAIProvider:
    """Test OpenAIProvider (requires API key)."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider."""
        return OpenAIProvider(model_name="gpt-4o-mini")

    def test_initialization_attributes(self, provider):
        """Provider has correct attributes."""
        assert provider.provider_name == "OpenAIProvider"
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_requires_api_key(self, provider):
        """Initialize fails without API key."""
        provider.api_key = None

        with pytest.raises(RuntimeError, match="API_KEY"):
            await provider.initialize()

    def test_get_health(self, provider):
        """Health status works."""
        health = provider.get_health()
        assert health.provider_name == "OpenAIProvider"
        assert isinstance(health, ProviderHealth)


class TestProviderPolymorphism:
    """Test that all providers implement common interface."""

    @pytest.mark.asyncio
    async def test_mock_provider_implements_interface(self):
        """MockProvider implements AIProvider interface."""
        provider: AIProvider = MockProvider()
        await provider.initialize()

        # Test interface methods
        result = await provider.generate("test")
        assert isinstance(result, str)

        embedding = await provider.embed("test")
        assert isinstance(embedding, list)

        health = provider.get_health()
        assert isinstance(health, ProviderHealth)

    def test_all_providers_return_health(self):
        """All providers return ProviderHealth objects."""
        providers = [
            MockProvider(),
            QwenProvider(),
            OllamaProvider(),
            OpenAIProvider(),
        ]

        for provider in providers:
            health = provider.get_health()
            assert isinstance(health, ProviderHealth)
            assert health.provider_name == provider.provider_name
