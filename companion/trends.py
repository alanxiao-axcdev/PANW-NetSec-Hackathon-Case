"""Emotional trends visualization module."""

from collections import Counter
from datetime import UTC, date, datetime, timedelta

from rich.console import Console
from rich.panel import Panel

from companion.journal import get_entries_by_date_range, get_recent_entries
from companion.models import JournalEntry, Sentiment

console = Console()


def show_trends(
    period: str = "week",
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """Display emotional trends dashboard.

    Shows:
    - Emotional delta (trending improving/declining)
    - Top themes frequency bars
    - Sentiment distribution breakdown

    Args:
        period: "week", "month", or "all"
        start_date: Custom start (overrides period)
        end_date: Custom end (overrides period)
    """
    date_start, date_end = _get_date_range(period, start_date, end_date)

    if start_date or end_date:
        entries = get_entries_by_date_range(date_start, date_end)
    elif period == "all":
        entries = get_recent_entries(limit=1000)
    else:
        entries = get_entries_by_date_range(date_start, date_end)

    if not entries:
        console.print("[yellow]No entries found for the selected period.[/yellow]")
        return

    delta = _calculate_emotional_delta(entries)
    themes = _count_theme_frequencies(entries)
    distribution = _calculate_sentiment_distribution(entries)

    _render_dashboard(entries, delta, themes, distribution, (date_start, date_end))


def _get_date_range(
    period: str, start: date | None, end: date | None
) -> tuple[date, date]:
    """Calculate start and end dates for period."""
    if start and end:
        return start, end

    today = datetime.now(tz=UTC).date()

    if period == "week":
        date_start = today - timedelta(days=7)
        date_end = today
    elif period == "month":
        date_start = today - timedelta(days=30)
        date_end = today
    else:
        date_start = date(2020, 1, 1)
        date_end = today

    return date_start, date_end


def _calculate_emotional_delta(entries: list[JournalEntry]) -> dict[str, float | str]:
    """Calculate if sentiment is improving/declining with percentage.

    Compare first half vs second half of period.
    Return: {"trend": "improving"|"declining"|"stable", "change": float}
    """
    if len(entries) < 2:
        return {"trend": "stable", "change": 0.0, "start": 0.5, "end": 0.5}

    entries_sorted = sorted(entries, key=lambda e: e.timestamp)
    mid = len(entries_sorted) // 2

    first_half = entries_sorted[:mid]
    second_half = entries_sorted[mid:]

    def _avg_sentiment(entry_list: list[JournalEntry]) -> float:
        scores: list[float] = []
        for entry in entry_list:
            sentiment: Sentiment | None = entry.sentiment
            if sentiment is not None:
                if sentiment.label == "positive":
                    scores.append(sentiment.confidence)
                elif sentiment.label == "negative":
                    scores.append(1.0 - sentiment.confidence)
                else:
                    scores.append(0.5)
        return sum(scores) / len(scores) if scores else 0.5

    first_avg = _avg_sentiment(first_half)
    second_avg = _avg_sentiment(second_half)

    change = (second_avg - first_avg) * 100

    trend: str
    if abs(change) < 5:
        trend = "stable"
    elif change > 0:
        trend = "improving"
    else:
        trend = "declining"

    return {
        "trend": trend,
        "change": abs(change),
        "start": first_avg,
        "end": second_avg,
    }


def _count_theme_frequencies(entries: list[JournalEntry]) -> Counter[str]:
    """Count theme occurrences across entries."""
    all_themes: list[str] = []
    for entry in entries:
        all_themes.extend(entry.themes)
    return Counter(all_themes)


def _calculate_sentiment_distribution(entries: list[JournalEntry]) -> dict[str, float]:
    """Calculate positive/neutral/negative percentages."""
    if not entries:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    counts = {"positive": 0, "neutral": 0, "negative": 0}

    for entry in entries:
        sentiment: Sentiment | None = entry.sentiment
        if sentiment is not None:
            counts[sentiment.label] += 1

    total = sum(counts.values())
    if total == 0:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    return {
        "positive": counts["positive"] / total,
        "neutral": counts["neutral"] / total,
        "negative": counts["negative"] / total,
    }


def _render_dashboard(
    entries: list[JournalEntry],
    delta: dict[str, float | str],
    themes: Counter[str],
    distribution: dict[str, float],
    date_range: tuple[date, date],
) -> None:
    """Render Rich-formatted dashboard to terminal."""
    start_date, end_date = date_range

    title = f"Emotional Trends ({start_date.strftime('%b %d')}-{end_date.strftime('%b %d, %Y')})"

    content: list[str] = []

    start_score = float(delta["start"])
    end_score = float(delta["end"])
    trend_str = str(delta["trend"])
    change_pct = float(delta["change"])

    content.append("[bold]Emotional Journey[/bold]")
    content.append(f"  Start of period:  {start_score:.2f} (Neutral-leaning)")
    content.append(f"  End of period:    {end_score:.2f} ({'Positive' if end_score > 0.6 else 'Neutral' if end_score > 0.4 else 'Negative'})")
    content.append("")

    trend_symbol = "^" if trend_str == "improving" else "v" if trend_str == "declining" else "-"
    trend_color = "green" if trend_str == "improving" else "red" if trend_str == "declining" else "yellow"
    content.append(f"  Trend: [{trend_color}]{trend_symbol} {trend_str.capitalize()} ({change_pct:.0f}%)[/{trend_color}]")
    content.append("")

    content.append("[bold]Top Themes[/bold]")
    top_themes = themes.most_common(5)
    if top_themes:
        max_count = top_themes[0][1]
        for theme, count in top_themes:
            bar_length = int((count / max_count) * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            content.append(f"  {theme:<14} {bar} ({count} entries)")
    else:
        content.append("  No themes detected")
    content.append("")

    content.append("[bold]Emotional Distribution[/bold]")
    for label, pct in distribution.items():
        bar_length = int(pct * 20)
        bar = "█" * bar_length
        color = "green" if label == "positive" else "red" if label == "negative" else "yellow"
        content.append(f"  {label.capitalize():<9} {int(pct * 100):>2}% [{color}]{bar}[/{color}]")

    content.append("")
    content.append(f"[dim]{len(entries)} entries analyzed[/dim]")

    panel = Panel("\n".join(content), title=title, border_style="blue")
    console.print(panel)
