"""Tests for AI engine module."""

import pytest

from companion import ai_engine
from companion.ai_backend.mock_provider import MockProvider


@pytest.fixture
def reset_engine():
    """Reset AI engine state between tests."""
    ai_engine._provider = None
    ai_engine._initialized = False
    yield
    ai_engine._provider = None
    ai_engine._initialized = False


@pytest.mark.asyncio
async def test_initialize_model(reset_engine):
    """Test model initialization."""
    await ai_engine.initialize_model()

    assert ai_engine.is_initialized()
    assert ai_engine._provider is not None
    assert isinstance(ai_engine._provider, MockProvider)


@pytest.mark.asyncio
async def test_initialize_model_idempotent(reset_engine):
    """Test that multiple initializations are safe."""
    await ai_engine.initialize_model()
    provider1 = ai_engine._provider

    await ai_engine.initialize_model()
    provider2 = ai_engine._provider

    assert provider1 is provider2


@pytest.mark.asyncio
async def test_generate_text(reset_engine):
    """Test text generation."""
    result = await ai_engine.generate_text("What is sentiment?")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_text_empty_prompt(reset_engine):
    """Test that empty prompt raises error."""
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await ai_engine.generate_text("")


@pytest.mark.asyncio
async def test_generate_text_auto_initializes(reset_engine):
    """Test that generation auto-initializes if needed."""
    assert not ai_engine.is_initialized()

    result = await ai_engine.generate_text("test")

    assert ai_engine.is_initialized()
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_generate_embedding(reset_engine):
    """Test embedding generation."""
    result = await ai_engine.generate_embedding("test text")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(x, float) for x in result)


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(reset_engine):
    """Test that empty text raises error."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await ai_engine.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_consistency(reset_engine):
    """Test that same text produces same embedding."""
    text = "consistent text"

    embedding1 = await ai_engine.generate_embedding(text)
    embedding2 = await ai_engine.generate_embedding(text)

    assert embedding1 == embedding2


def test_ensure_model_downloaded(reset_engine):
    """Test model download check."""
    result = ai_engine.ensure_model_downloaded()
    assert isinstance(result, bool)
    assert result is True


def test_is_initialized_false(reset_engine):
    """Test is_initialized returns False when not initialized."""
    assert ai_engine.is_initialized() is False


@pytest.mark.asyncio
async def test_is_initialized_true(reset_engine):
    """Test is_initialized returns True after initialization."""
    await ai_engine.initialize_model()
    assert ai_engine.is_initialized() is True


@pytest.mark.asyncio
async def test_shutdown(reset_engine):
    """Test engine shutdown."""
    await ai_engine.initialize_model()
    assert ai_engine.is_initialized()

    await ai_engine.shutdown()

    assert not ai_engine.is_initialized()
    assert ai_engine._provider is None
