"""Tests for summarizer module."""

from datetime import date, datetime

import pytest

from companion import summarizer
from companion.models import JournalEntry, Sentiment, Summary


@pytest.mark.asyncio
async def test_generate_summary_week():
    """Test weekly summary generation."""
    entries = [
        JournalEntry(
            content="Entry 1",
            themes=["work", "health"],
            sentiment=Sentiment(label="positive", confidence=0.8),
        ),
        JournalEntry(
            content="Entry 2",
            themes=["work", "family"],
            sentiment=Sentiment(label="neutral", confidence=0.7),
        ),
    ]

    result = await summarizer.generate_summary(entries, "week")

    assert isinstance(result, Summary)
    assert result.period == "week"
    assert result.entry_count == 2
    assert len(result.dominant_themes) > 0
    assert len(result.emotional_trend) > 0


@pytest.mark.asyncio
async def test_generate_summary_month():
    """Test monthly summary generation."""
    entries = [
        JournalEntry(
            content="Entry 1",
            themes=["work"],
            sentiment=Sentiment(label="positive", confidence=0.9),
        ),
    ]

    result = await summarizer.generate_summary(entries, "month")

    assert isinstance(result, Summary)
    assert result.period == "month"
    assert result.entry_count == 1


@pytest.mark.asyncio
async def test_generate_summary_empty():
    """Test that empty entries raises error."""
    with pytest.raises(ValueError, match="Cannot generate summary from empty"):
        await summarizer.generate_summary([], "week")


@pytest.mark.asyncio
async def test_generate_summary_invalid_period():
    """Test that invalid period raises error."""
    entries = [JournalEntry(content="Test")]

    with pytest.raises(ValueError, match="Invalid period"):
        await summarizer.generate_summary(entries, "year")  # type: ignore


@pytest.mark.asyncio
async def test_identify_patterns():
    """Test pattern identification."""
    entries = [
        JournalEntry(content="Work entry", themes=["work"], word_count=50),
        JournalEntry(content="Work entry 2", themes=["work"], word_count=60),
        JournalEntry(content="Work entry 3", themes=["work"], word_count=55),
    ]

    result = await summarizer.identify_patterns(entries)

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(p, str) for p in result)


@pytest.mark.asyncio
async def test_identify_patterns_empty():
    """Test that empty entries raises error."""
    with pytest.raises(ValueError, match="Cannot identify patterns from empty"):
        await summarizer.identify_patterns([])


def test_format_summary():
    """Test summary formatting."""
    summary = Summary(
        period="week",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 7),
        entry_count=5,
        dominant_themes=["work", "health"],
        emotional_trend="Mostly positive",
        insights=["You wrote consistently", "Focus on work-life balance"],
    )

    result = summarizer.format_summary(summary)

    assert isinstance(result, str)
    assert "Week Summary" in result
    assert "2025-01-01" in result
    assert "work" in result
    assert "Mostly positive" in result


def test_get_week_date_range():
    """Test getting current week date range."""
    start, end = summarizer.get_week_date_range()

    assert isinstance(start, date)
    assert isinstance(end, date)
    assert start <= end
    assert (end - start).days == 6
    assert start.weekday() == 0


def test_get_month_date_range():
    """Test getting current month date range."""
    start, end = summarizer.get_month_date_range()

    assert isinstance(start, date)
    assert isinstance(end, date)
    assert start <= end
    assert start.day == 1


@pytest.mark.asyncio
async def test_generate_period_summary():
    """Test custom period summary."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 7)

    entries = [
        JournalEntry(
            content="Entry 1",
            themes=["work"],
            sentiment=Sentiment(label="positive", confidence=0.8),
            timestamp=datetime.combine(start, datetime.min.time()),
        ),
    ]

    result = await summarizer.generate_period_summary(entries, start, end)

    assert isinstance(result, Summary)
    assert result.period in ["week", "month"]
    assert result.entry_count == 1


@pytest.mark.asyncio
async def test_generate_period_summary_invalid_dates():
    """Test that invalid dates raise error."""
    entries = [JournalEntry(content="Test")]
    start = date(2025, 1, 10)
    end = date(2025, 1, 1)

    with pytest.raises(ValueError, match="Start date must be before"):
        await summarizer.generate_period_summary(entries, start, end)


@pytest.mark.asyncio
async def test_generate_period_summary_empty():
    """Test that empty entries raises error."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 7)

    with pytest.raises(ValueError, match="Cannot generate summary from empty"):
        await summarizer.generate_period_summary([], start, end)


def test_format_emotional_trend_positive():
    """Test emotional trend formatting for positive trend."""
    trend = {"positive": 0.7, "neutral": 0.2, "negative": 0.1}

    result = summarizer._format_emotional_trend(trend)

    assert "Mostly positive" in result
    assert "70%" in result


def test_format_emotional_trend_negative():
    """Test emotional trend formatting for negative trend."""
    trend = {"positive": 0.1, "neutral": 0.2, "negative": 0.7}

    result = summarizer._format_emotional_trend(trend)

    assert "challenging" in result.lower()
    assert "70%" in result


def test_format_emotional_trend_balanced():
    """Test emotional trend formatting for balanced trend."""
    trend = {"positive": 0.2, "neutral": 0.6, "negative": 0.2}

    result = summarizer._format_emotional_trend(trend)

    assert "balanced" in result.lower()
    assert "60%" in result
