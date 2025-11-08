"""Tests for prompter module."""

from datetime import datetime

import pytest

from companion import prompter
from companion.models import JournalEntry


@pytest.mark.asyncio
async def test_get_reflection_prompt():
    """Test reflection prompt generation."""
    entries = [
        JournalEntry(content="Entry 1", themes=["work"]),
        JournalEntry(content="Entry 2", themes=["family"]),
    ]
    current_time = datetime.now()

    result = await prompter.get_reflection_prompt(entries, current_time)

    assert isinstance(result, str)
    assert len(result) > 0
    assert result.endswith("?")


@pytest.mark.asyncio
async def test_get_reflection_prompt_no_entries():
    """Test prompt generation with no entries."""
    result = await prompter.get_reflection_prompt([], datetime.now())

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_continuation_prompt():
    """Test continuation prompt generation."""
    current_text = "Today was interesting because"

    result = await prompter.get_continuation_prompt(current_text)

    assert isinstance(result, str)
    assert len(result) > 0
    assert result.endswith("?")


@pytest.mark.asyncio
async def test_get_continuation_prompt_empty():
    """Test that empty text raises error."""
    with pytest.raises(ValueError, match="Current text cannot be empty"):
        await prompter.get_continuation_prompt("")


@pytest.mark.asyncio
async def test_get_placeholder_text():
    """Test placeholder text generation."""
    current_text = "I'm writing about my day"
    idle_duration = 20.0
    entries = [JournalEntry(content="Previous entry")]

    result = await prompter.get_placeholder_text(
        current_text,
        idle_duration,
        entries,
    )

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_get_placeholder_text_short_idle():
    """Test that short idle returns empty string."""
    result = await prompter.get_placeholder_text("text", 5.0, [])
    assert result == ""


@pytest.mark.asyncio
async def test_get_placeholder_text_negative_duration():
    """Test that negative duration raises error."""
    with pytest.raises(ValueError, match="Idle duration cannot be negative"):
        await prompter.get_placeholder_text("text", -1.0, [])


def test_get_first_time_prompt():
    """Test first-time user prompt."""
    result = prompter.get_first_time_prompt()

    assert isinstance(result, str)
    assert len(result) > 0
    assert "?" in result


@pytest.mark.asyncio
async def test_get_time_based_prompt():
    """Test time-based prompt generation."""
    result = await prompter.get_time_based_prompt(hour=9)

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_time_based_prompt_invalid_hour():
    """Test that invalid hour raises error."""
    with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
        await prompter.get_time_based_prompt(hour=25)


@pytest.mark.asyncio
async def test_get_time_based_prompt_default():
    """Test time-based prompt with current time."""
    result = await prompter.get_time_based_prompt()

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_followup_prompts():
    """Test follow-up prompt generation."""
    entry = JournalEntry(
        content="I had a great day at work today",
        themes=["work", "happiness"],
    )

    result = await prompter.generate_followup_prompts(entry, count=3)

    assert isinstance(result, list)
    assert len(result) <= 3
    assert all(isinstance(p, str) for p in result)
    assert all(p.endswith("?") for p in result)


@pytest.mark.asyncio
async def test_generate_followup_prompts_empty_content():
    """Test that empty content raises error."""
    entry = JournalEntry(content="")

    with pytest.raises(ValueError, match="Entry content cannot be empty"):
        await prompter.generate_followup_prompts(entry)


@pytest.mark.asyncio
async def test_generate_followup_prompts_invalid_count():
    """Test that invalid count raises error."""
    entry = JournalEntry(content="Test content")

    with pytest.raises(ValueError, match="Count must be at least 1"):
        await prompter.generate_followup_prompts(entry, count=0)


def test_get_time_context_morning():
    """Test time context for morning."""
    morning_time = datetime(2025, 1, 1, 8, 0)
    result = prompter._get_time_context(morning_time)
    assert result == "morning"


def test_get_time_context_afternoon():
    """Test time context for afternoon."""
    afternoon_time = datetime(2025, 1, 1, 14, 0)
    result = prompter._get_time_context(afternoon_time)
    assert result == "afternoon"


def test_get_time_context_evening():
    """Test time context for evening."""
    evening_time = datetime(2025, 1, 1, 19, 0)
    result = prompter._get_time_context(evening_time)
    assert result == "evening"


def test_get_theme_context_no_entries():
    """Test theme context with no entries."""
    result = prompter._get_theme_context([])
    assert result == "no previous entries"


def test_get_theme_context_with_themes():
    """Test theme context extraction."""
    entries = [
        JournalEntry(content="Entry 1", themes=["work", "health"]),
        JournalEntry(content="Entry 2", themes=["work"]),
    ]

    result = prompter._get_theme_context(entries)
    assert "work" in result
