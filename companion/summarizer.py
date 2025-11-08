"""Weekly and monthly journal summaries.

Generates human-readable summaries of journal entries, identifying patterns,
emotional trends, and key insights across time periods.
"""

import logging
from collections import Counter
from datetime import date, timedelta
from typing import Literal

from companion import ai_engine
from companion.analyzer import get_dominant_themes, get_emotional_trend
from companion.models import JournalEntry, Summary

logger = logging.getLogger(__name__)


async def generate_summary(
    entries: list[JournalEntry],
    period: Literal["week", "month"],
) -> Summary:
    """Generate summary for journal entries.

    Creates comprehensive summary including dominant themes,
    emotional trends, and AI-generated insights.

    Args:
        entries: List of journal entries to summarize
        period: Summary period (week or month)

    Returns:
        Summary object with analysis and insights

    Raises:
        ValueError: If entries is empty or period is invalid
    """
    if not entries:
        msg = "Cannot generate summary from empty entries"
        raise ValueError(msg)

    if period not in ["week", "month"]:
        msg = f"Invalid period: {period}. Must be 'week' or 'month'"
        raise ValueError(msg)

    entries_sorted = sorted(entries, key=lambda e: e.timestamp)
    start_date = entries_sorted[0].timestamp.date()
    end_date = entries_sorted[-1].timestamp.date()

    dominant_themes_list = get_dominant_themes(entries, top_n=5)
    dominant_theme_names = [theme for theme, _ in dominant_themes_list]

    emotional_trend_data = await get_emotional_trend(entries)
    emotional_trend_text = _format_emotional_trend(emotional_trend_data)

    await identify_patterns(entries)

    insights = await _generate_insights(entries, period)

    summary = Summary(
        period=period,
        start_date=start_date,
        end_date=end_date,
        entry_count=len(entries),
        dominant_themes=dominant_theme_names,
        emotional_trend=emotional_trend_text,
        insights=insights,
    )

    logger.info(
        "Generated %s summary: %d entries, %d themes, %d insights",
        period,
        len(entries),
        len(dominant_theme_names),
        len(insights),
    )

    return summary


def _format_emotional_trend(trend_data: dict[str, float]) -> str:
    """Format emotional trend into human-readable text.

    Args:
        trend_data: Dictionary with sentiment percentages

    Returns:
        Human-readable description of emotional trend
    """
    positive_pct = trend_data.get("positive", 0.0) * 100
    neutral_pct = trend_data.get("neutral", 0.0) * 100
    negative_pct = trend_data.get("negative", 0.0) * 100

    if positive_pct > 50:
        return f"Mostly positive ({positive_pct:.0f}% positive, {negative_pct:.0f}% negative)"
    if negative_pct > 50:
        return f"Mostly challenging ({negative_pct:.0f}% negative, {positive_pct:.0f}% positive)"
    if neutral_pct > 50:
        return f"Generally balanced ({neutral_pct:.0f}% neutral)"
    return f"Mixed emotions (positive: {positive_pct:.0f}%, neutral: {neutral_pct:.0f}%, negative: {negative_pct:.0f}%)"


async def identify_patterns(entries: list[JournalEntry]) -> list[str]:
    """Identify recurring patterns across entries.

    Analyzes entries to find behavioral patterns, recurring themes,
    and notable changes over time.

    Args:
        entries: List of journal entries

    Returns:
        List of pattern descriptions

    Raises:
        ValueError: If entries is empty
    """
    if not entries:
        msg = "Cannot identify patterns from empty entries"
        raise ValueError(msg)

    patterns = []

    theme_counter: Counter[str] = Counter()
    for entry in entries:
        theme_counter.update(entry.themes)

    if theme_counter:
        most_common = theme_counter.most_common(1)[0]
        if most_common[1] >= 3:
            patterns.append(f"Recurring focus on {most_common[0]} (mentioned {most_common[1]} times)")

    word_counts = [entry.word_count for entry in entries]
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0

    if avg_words > 200:
        patterns.append(f"Detailed entries (average {avg_words:.0f} words)")
    elif avg_words < 50:
        patterns.append(f"Brief entries (average {avg_words:.0f} words)")

    if len(entries) >= 3:
        recent_sentiment = [e.sentiment.label if e.sentiment else "neutral" for e in entries[-3:]]
        if all(s == "positive" for s in recent_sentiment):
            patterns.append("Increasingly positive mood in recent entries")
        elif all(s == "negative" for s in recent_sentiment):
            patterns.append("Challenging emotions in recent entries")

    entries_per_week = len(entries) / max(1, (entries[-1].timestamp - entries[0].timestamp).days / 7)
    if entries_per_week >= 5:
        patterns.append("Very consistent writing practice")
    elif entries_per_week >= 3:
        patterns.append("Regular writing habit")

    logger.debug("Identified %d patterns", len(patterns))
    return patterns


async def _generate_insights(
    entries: list[JournalEntry],
    period: Literal["week", "month"],
) -> list[str]:
    """Generate AI insights from entries.

    Args:
        entries: Journal entries to analyze
        period: Time period being summarized

    Returns:
        List of insight strings
    """
    if not entries:
        return []

    entry_summaries = []
    for entry in entries[:5]:
        snippet = entry.content[:100].replace("\n", " ")
        sentiment = entry.sentiment.label if entry.sentiment else "neutral"
        entry_summaries.append(f"- {sentiment}: {snippet}...")

    entries_text = "\n".join(entry_summaries)

    prompt = f"""Analyze these journal entries from the past {period} and provide 3-4 brief insights about patterns, growth, or areas to explore further. Each insight should be one sentence.

Entries:
{entries_text}

Insights (one per line):"""

    try:
        response = await ai_engine.generate_text(prompt, max_tokens=200)
        insights = [
            line.strip().lstrip("123456789.-) ")
            for line in response.strip().split("\n")
            if line.strip() and len(line.strip()) > 10
        ]

        logger.debug("Generated %d insights", len(insights))
        return insights[:4]

    except Exception as e:
        logger.warning("Failed to generate AI insights: %s", e)
        return [
            f"You wrote {len(entries)} entries this {period}",
            "Consider reflecting on recurring themes in upcoming entries",
        ]


def format_summary(summary: Summary) -> str:
    """Format summary as human-readable text.

    Args:
        summary: Summary object to format

    Returns:
        Formatted text suitable for display
    """
    lines = []

    lines.append(f"# {summary.period.title()} Summary")
    lines.append(f"{summary.start_date} to {summary.end_date}")
    lines.append("")

    lines.append(f"**Entries**: {summary.entry_count}")
    lines.append("")

    if summary.dominant_themes:
        lines.append("**Dominant Themes**:")
        for theme in summary.dominant_themes:
            lines.append(f"  - {theme}")
        lines.append("")

    lines.append(f"**Emotional Trend**: {summary.emotional_trend}")
    lines.append("")

    if summary.insights:
        lines.append("**Insights**:")
        for insight in summary.insights:
            lines.append(f"  - {insight}")
        lines.append("")

    return "\n".join(lines)


def get_week_date_range() -> tuple[date, date]:
    """Get date range for current week (Monday to Sunday).

    Returns:
        Tuple of (start_date, end_date) for current week
    """
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    return start_of_week, end_of_week


def get_month_date_range() -> tuple[date, date]:
    """Get date range for current month.

    Returns:
        Tuple of (start_date, end_date) for current month
    """
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    if today.month == 12:
        end_of_month = date(today.year, 12, 31)
    else:
        next_month = date(today.year, today.month + 1, 1)
        end_of_month = next_month - timedelta(days=1)

    return start_of_month, end_of_month


async def generate_period_summary(
    entries: list[JournalEntry],
    start_date: date,
    end_date: date,
) -> Summary:
    """Generate summary for custom date range.

    Args:
        entries: Journal entries in date range
        start_date: Period start
        end_date: Period end

    Returns:
        Summary for the period

    Raises:
        ValueError: If entries is empty or dates are invalid
    """
    if not entries:
        msg = "Cannot generate summary from empty entries"
        raise ValueError(msg)

    if start_date > end_date:
        msg = "Start date must be before or equal to end date"
        raise ValueError(msg)

    days_diff = (end_date - start_date).days

    if days_diff <= 7:
        period: Literal["week", "month"] = "week"
    else:
        period = "month"

    return await generate_summary(entries, period)
