"""Dynamic prompt generation for journaling.

Generates context-aware prompts based on user's writing history,
current time, and idle duration to encourage reflection.
"""

import logging
from datetime import datetime

from companion import ai_engine
from companion.models import JournalEntry

logger = logging.getLogger(__name__)


async def get_reflection_prompt(
    recent_entries: list[JournalEntry],
    current_time: datetime,
) -> str:
    """Generate reflection prompt based on context.

    Creates personalized prompt considering recent entries,
    time of day, and recurring themes.

    Args:
        recent_entries: User's recent journal entries (up to 5)
        current_time: Current datetime

    Returns:
        Generated prompt text

    Raises:
        RuntimeError: If prompt generation fails
    """
    time_context = _get_time_context(current_time)
    theme_context = _get_theme_context(recent_entries)

    prompt_text = f"""Generate a thoughtful journal prompt for someone writing at {time_context}.

Recent themes in their journal: {theme_context}

Generate one simple, open-ended question that encourages reflection. Keep it under 15 words.

Prompt:"""

    try:
        response = await ai_engine.generate_text(prompt_text, max_tokens=50)
        generated_prompt = response.strip()

        if not generated_prompt.endswith("?"):
            generated_prompt += "?"

        logger.debug("Generated reflection prompt: %s", generated_prompt)
        return generated_prompt

    except Exception as e:
        logger.warning("Failed to generate AI prompt, using fallback: %s", e)
        return _get_fallback_prompt(current_time)


def _get_time_context(current_time: datetime) -> str:
    """Get time-of-day context string.

    Args:
        current_time: Current datetime

    Returns:
        Time context description (e.g., "early morning", "late evening")
    """
    hour = current_time.hour

    if hour < 6:
        return "late night"
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    if hour < 21:
        return "evening"
    return "night"


def _get_theme_context(entries: list[JournalEntry]) -> str:
    """Extract theme context from recent entries.

    Args:
        entries: Recent journal entries

    Returns:
        Comma-separated theme summary or "no previous entries"
    """
    if not entries:
        return "no previous entries"

    all_themes = []
    for entry in entries:
        all_themes.extend(entry.themes)

    if not all_themes:
        return "general reflection"

    from collections import Counter
    theme_counts = Counter(all_themes)
    top_themes = [theme for theme, _ in theme_counts.most_common(3)]

    return ", ".join(top_themes) if top_themes else "general reflection"


def _get_fallback_prompt(current_time: datetime) -> str:
    """Get time-appropriate fallback prompt.

    Used when AI generation fails.

    Args:
        current_time: Current datetime

    Returns:
        Static prompt based on time of day
    """
    hour = current_time.hour

    if hour < 12:
        return "What are you looking forward to today?"
    if hour < 17:
        return "How is your day going so far?"
    if hour < 21:
        return "What was the best part of your day?"
    return "What are you grateful for today?"


async def get_continuation_prompt(current_text: str) -> str:
    """Generate continuation prompt based on current writing.

    Suggests a natural follow-up question based on what user
    has written so far.

    Args:
        current_text: Text user has written in current session

    Returns:
        Continuation prompt

    Raises:
        ValueError: If current_text is empty
    """
    if not current_text or not current_text.strip():
        msg = "Current text cannot be empty"
        raise ValueError(msg)

    prompt_text = f"""Based on this journal entry in progress, suggest one follow-up question to help them explore further. Keep it under 15 words.

Entry so far: {current_text[-200:]}

Follow-up question:"""

    try:
        response = await ai_engine.generate_text(prompt_text, max_tokens=50)
        continuation = response.strip()

        if not continuation.endswith("?"):
            continuation += "?"

        logger.debug("Generated continuation prompt: %s", continuation)
        return continuation

    except Exception as e:
        logger.warning("Failed to generate continuation prompt: %s", e)
        return "What else comes to mind?"


async def get_placeholder_text(
    current_text: str,
    idle_duration: float,
    recent_entries: list[JournalEntry],
) -> str:
    """Get placeholder text for idle state.

    Shows helpful prompt when user pauses writing for a period.

    Args:
        current_text: What user has written so far
        idle_duration: Seconds since last keystroke
        recent_entries: Recent journal entries for context

    Returns:
        Placeholder text to display

    Raises:
        ValueError: If idle_duration is negative
    """
    if idle_duration < 0:
        msg = "Idle duration cannot be negative"
        raise ValueError(msg)

    if idle_duration < 10:
        return ""

    if not current_text or len(current_text) < 20:
        current_time = datetime.now()
        return await get_reflection_prompt(recent_entries, current_time)

    if idle_duration >= 15:
        return await get_continuation_prompt(current_text)

    return "Keep writing..."


def get_first_time_prompt() -> str:
    """Get welcoming prompt for first-time users.

    Returns:
        Welcome prompt for new users
    """
    prompts = [
        "Welcome! What's on your mind today?",
        "Let's start your journal. How are you feeling right now?",
        "Welcome to your journal. What would you like to write about?",
        "Hi there! What brings you here today?",
    ]

    import random
    return random.choice(prompts)


async def get_time_based_prompt(hour: int | None = None) -> str:
    """Get prompt based on specific hour.

    Args:
        hour: Hour of day (0-23), or None for current hour

    Returns:
        Time-appropriate prompt

    Raises:
        ValueError: If hour is invalid
    """
    if hour is None:
        hour = datetime.now().hour

    if not 0 <= hour <= 23:
        msg = "Hour must be between 0 and 23"
        raise ValueError(msg)

    if hour < 6:
        return "What's keeping you up tonight?"
    if hour < 9:
        return "What are your intentions for today?"
    if hour < 12:
        return "How's your morning going?"
    if hour < 14:
        return "What's on your mind this afternoon?"
    if hour < 17:
        return "How is your day unfolding?"
    if hour < 20:
        return "What stood out to you today?"
    if hour < 23:
        return "How are you feeling this evening?"
    return "What's on your mind as the day ends?"


async def generate_followup_prompts(entry: JournalEntry, count: int = 3) -> list[str]:
    """Generate follow-up prompts for next session.

    Creates prompts based on themes and content from current entry
    to encourage continued reflection.

    Args:
        entry: Journal entry to base prompts on
        count: Number of prompts to generate (default: 3)

    Returns:
        List of follow-up prompt strings

    Raises:
        ValueError: If entry content is empty or count is invalid
    """
    if not entry.content or not entry.content.strip():
        msg = "Entry content cannot be empty"
        raise ValueError(msg)

    if count < 1:
        msg = "Count must be at least 1"
        raise ValueError(msg)

    theme_context = ", ".join(entry.themes) if entry.themes else "general reflection"

    prompt_text = f"""Based on this journal entry with themes: {theme_context}, generate {count} thoughtful follow-up questions for their next session. Each question should be under 15 words.

Entry: {entry.content[:300]}

Questions (one per line):"""

    try:
        response = await ai_engine.generate_text(prompt_text, max_tokens=150)
        prompts = [
            line.strip().lstrip("123456789.-) ")
            for line in response.strip().split("\n")
            if line.strip()
        ]

        prompts = [p if p.endswith("?") else p + "?" for p in prompts]

        logger.debug("Generated %d follow-up prompts", len(prompts[:count]))
        return prompts[:count]

    except Exception as e:
        logger.warning("Failed to generate follow-up prompts: %s", e)
        return [
            "What else would you like to explore?",
            "How did this make you feel?",
            "What insights did you gain?",
        ][:count]
