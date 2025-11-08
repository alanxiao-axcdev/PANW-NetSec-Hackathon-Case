"""Tests for analyzer module."""

import pytest

from companion import analyzer
from companion.models import JournalEntry
from companion.models import Sentiment


@pytest.mark.asyncio
async def test_analyze_sentiment():
    """Test sentiment analysis."""
    text = "I had a wonderful day today!"

    result = await analyzer.analyze_sentiment(text)

    assert isinstance(result, Sentiment)
    assert result.label in ["positive", "neutral", "negative"]
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_analyze_sentiment_empty():
    """Test that empty text raises error."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await analyzer.analyze_sentiment("")


@pytest.mark.asyncio
async def test_extract_themes():
    """Test theme extraction."""
    text = "I went to work today and had a meeting about the project."

    result = await analyzer.extract_themes(text)

    assert isinstance(result, list)
    assert all(hasattr(theme, "name") for theme in result)
    assert all(hasattr(theme, "confidence") for theme in result)
    assert all(0.0 <= theme.confidence <= 1.0 for theme in result)


@pytest.mark.asyncio
async def test_extract_themes_empty():
    """Test that empty text raises error."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await analyzer.extract_themes("")


@pytest.mark.asyncio
async def test_get_emotional_trend():
    """Test emotional trend calculation."""
    entries = [
        JournalEntry(
            content="Great day!",
            sentiment=Sentiment(label="positive", confidence=0.9),
        ),
        JournalEntry(
            content="Okay day",
            sentiment=Sentiment(label="neutral", confidence=0.7),
        ),
        JournalEntry(
            content="Bad day",
            sentiment=Sentiment(label="negative", confidence=0.8),
        ),
    ]

    result = await analyzer.get_emotional_trend(entries)

    assert isinstance(result, dict)
    assert "positive" in result
    assert "neutral" in result
    assert "negative" in result
    assert abs(sum(result.values()) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_get_emotional_trend_empty():
    """Test that empty list raises error."""
    with pytest.raises(ValueError, match="Entries list cannot be empty"):
        await analyzer.get_emotional_trend([])


def test_get_dominant_themes():
    """Test finding dominant themes."""
    entries = [
        JournalEntry(content="Entry 1", themes=["work", "health"]),
        JournalEntry(content="Entry 2", themes=["work", "family"]),
        JournalEntry(content="Entry 3", themes=["work", "exercise"]),
    ]

    result = analyzer.get_dominant_themes(entries, top_n=2)

    assert isinstance(result, list)
    assert len(result) <= 2
    assert result[0][0] == "work"
    assert result[0][1] == 3


def test_get_dominant_themes_empty():
    """Test that empty list raises error."""
    with pytest.raises(ValueError, match="Entries list cannot be empty"):
        analyzer.get_dominant_themes([])


def test_get_dominant_themes_negative_top_n():
    """Test that negative top_n raises error."""
    entries = [JournalEntry(content="Test", themes=["test"])]

    with pytest.raises(ValueError, match="top_n must be non-negative"):
        analyzer.get_dominant_themes(entries, top_n=-1)


@pytest.mark.asyncio
async def test_analyze_entry_batch():
    """Test batch analysis."""
    entries = [
        JournalEntry(content="Happy day"),
        JournalEntry(content="Sad day"),
        JournalEntry(content="Normal day"),
    ]

    result = await analyzer.analyze_entry_batch(entries)

    assert len(result) == len(entries)
    assert all(isinstance(e, JournalEntry) for e in result)


@pytest.mark.asyncio
async def test_analyze_entry_batch_empty():
    """Test that empty list raises error."""
    with pytest.raises(ValueError, match="Entries list cannot be empty"):
        await analyzer.analyze_entry_batch([])


@pytest.mark.asyncio
async def test_analyze_entry_batch_skips_analyzed():
    """Test that already-analyzed entries are skipped."""
    entries = [
        JournalEntry(
            content="Already analyzed",
            sentiment=Sentiment(label="positive", confidence=0.9),
            themes=["test"],
        ),
        JournalEntry(content="Needs analysis"),
    ]

    result = await analyzer.analyze_entry_batch(entries)

    assert len(result) == 2
    assert result[0].sentiment.label == "positive"
