"""Sentiment and theme analysis for journal entries.

Uses AI to classify emotional sentiment and extract recurring themes
from journal content.
"""

import asyncio
import logging
from collections import Counter

from companion import ai_engine
from companion.models import JournalEntry, Sentiment, Theme

logger = logging.getLogger(__name__)


async def analyze_sentiment(text: str) -> Sentiment:
    """Analyze sentiment of text.

    Uses AI to classify text as positive, neutral, or negative
    with confidence score.

    Args:
        text: Journal entry content to analyze

    Returns:
        Sentiment with label and confidence

    Raises:
        ValueError: If text is empty
        RuntimeError: If AI analysis fails
    """
    if not text or not text.strip():
        msg = "Text cannot be empty"
        raise ValueError(msg)

    prompt = f"""Analyze the sentiment of this journal entry.

Entry: "{text[:500]}"

Respond with ONLY ONE WORD (no explanation, no punctuation):
- positive (if the entry expresses positive emotions)
- neutral (if the entry is factual or balanced)
- negative (if the entry expresses negative emotions)

Your response (one word only):"""

    try:
        response = await ai_engine.generate_text(prompt, max_tokens=10)
        response_clean = response.strip().lower()

        # Extract sentiment word even if model adds extra text
        # Check first for exact matches (most reliable)
        first_word = response_clean.split()[0] if response_clean.split() else ""

        if first_word in ["positive", "negative", "neutral"]:
            sentiment_label = first_word
        # Fall back to substring search
        elif "positive" in response_clean:
            sentiment_label = "positive"
        elif "negative" in response_clean:
            sentiment_label = "negative"
        elif "neutral" in response_clean:
            sentiment_label = "neutral"
        # Use keyword-based fallback if AI gives unusable response
        else:
            logger.debug("AI response unclear: %s, using keyword fallback", response_clean[:50])
            sentiment_label = _fallback_sentiment_detection(text)

        confidence = _estimate_confidence(text, sentiment_label)

        logger.debug("Analyzed sentiment: %s (%.2f)", sentiment_label, confidence)
        return Sentiment(label=sentiment_label, confidence=confidence)  # type: ignore

    except Exception as e:
        logger.error("Sentiment analysis failed: %s", e)
        msg = f"Sentiment analysis failed: {e}"
        raise RuntimeError(msg) from e


def _estimate_confidence(text: str, sentiment: str) -> float:
    """Estimate confidence based on text characteristics.

    Simple heuristic based on presence of strong sentiment words.

    Args:
        text: Text content
        sentiment: Detected sentiment label

    Returns:
        Confidence score between 0.5 and 0.95
    """
    text_lower = text.lower()

    positive_words = ["happy", "great", "wonderful", "excellent", "joy", "love", "amazing", "fantastic"]
    negative_words = ["sad", "terrible", "awful", "hate", "angry", "frustrated", "disappointed", "bad"]

    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if sentiment == "positive":
        intensity = positive_count
    elif sentiment == "negative":
        intensity = negative_count
    else:
        intensity = 0

    base_confidence = 0.7
    return min(0.95, base_confidence + (intensity * 0.05))



async def extract_themes(text: str) -> list[Theme]:
    """Extract themes from journal entry.

    Uses AI to identify main topics and themes present in the text.

    Args:
        text: Journal entry content

    Returns:
        List of Theme objects with confidence scores

    Raises:
        ValueError: If text is empty
        RuntimeError: If AI analysis fails
    """
    if not text or not text.strip():
        msg = "Text cannot be empty"
        raise ValueError(msg)

    prompt = f"""Identify the main themes in this journal entry.

Entry: "{text[:500]}"

List 2-4 themes as comma-separated single words (e.g., work, family, health, stress).

Your response (comma-separated words only):"""

    try:
        response = await ai_engine.generate_text(prompt, max_tokens=30)

        # Clean response: extract only the comma-separated words
        # Remove any sentences or extra text
        response_clean = response.strip()

        # If response has newlines or periods, take only first line/sentence
        if '\n' in response_clean:
            response_clean = response_clean.split('\n')[0]
        if '.' in response_clean and response_clean.index('.') < 50:
            response_clean = response_clean.split('.')[0]

        theme_names = [t.strip().lower() for t in response_clean.split(",") if t.strip()]

        themes = [
            Theme(name=name, confidence=_theme_confidence(text, name))
            for name in theme_names[:4]
        ]

        logger.debug("Extracted %d themes: %s", len(themes), [t.name for t in themes])
        return themes

    except Exception as e:
        logger.error("Theme extraction failed: %s", e)
        msg = f"Theme extraction failed: {e}"
        raise RuntimeError(msg) from e


def _theme_confidence(text: str, theme: str) -> float:
    """Estimate theme relevance confidence.

    Args:
        text: Entry text
        theme: Theme name

    Returns:
        Confidence score between 0.6 and 0.9
    """
    text_lower = text.lower()
    theme_lower = theme.lower()

    occurrences = text_lower.count(theme_lower)

    base_confidence = 0.7
    return min(0.9, base_confidence + (occurrences * 0.05))



async def get_emotional_trend(entries: list[JournalEntry]) -> dict[str, float]:
    """Calculate emotional trend from multiple entries.

    Aggregates sentiment across entries to show overall emotional state.

    Args:
        entries: List of journal entries to analyze

    Returns:
        Dictionary with sentiment distribution:
        {"positive": 0.4, "neutral": 0.3, "negative": 0.3}

    Raises:
        ValueError: If entries list is empty
    """
    if not entries:
        msg = "Entries list cannot be empty"
        raise ValueError(msg)

    sentiment_counts: Counter[str] = Counter()
    total = 0

    for entry in entries:
        if entry.sentiment:
            sentiment_counts[entry.sentiment.label] += 1
            total += 1
        else:
            try:
                sentiment = await analyze_sentiment(entry.content)
                sentiment_counts[sentiment.label] += 1
                total += 1
            except Exception as e:
                logger.warning("Failed to analyze entry %s: %s", entry.id, e)
                continue

    if total == 0:
        logger.warning("No sentiments could be analyzed")
        return {"positive": 0.0, "neutral": 1.0, "negative": 0.0}

    trend = {
        "positive": sentiment_counts["positive"] / total,
        "neutral": sentiment_counts["neutral"] / total,
        "negative": sentiment_counts["negative"] / total,
    }

    logger.debug("Emotional trend: %s", trend)
    return trend


def get_dominant_themes(entries: list[JournalEntry], top_n: int = 5) -> list[tuple[str, int]]:
    """Find most common themes across entries.

    Args:
        entries: List of journal entries
        top_n: Number of top themes to return (default: 5)

    Returns:
        List of (theme_name, count) tuples, sorted by frequency

    Raises:
        ValueError: If entries is empty or top_n is negative
    """
    if not entries:
        msg = "Entries list cannot be empty"
        raise ValueError(msg)

    if top_n < 0:
        msg = "top_n must be non-negative"
        raise ValueError(msg)

    theme_counter: Counter[str] = Counter()

    for entry in entries:
        theme_counter.update(entry.themes)

    dominant = theme_counter.most_common(top_n)
    logger.debug("Top %d themes: %s", top_n, dominant)

    return dominant


async def analyze_entry_batch(entries: list[JournalEntry]) -> list[JournalEntry]:
    """Analyze multiple entries in parallel.

    Performs sentiment and theme analysis for all entries that don't
    already have analysis results.

    Args:
        entries: List of entries to analyze

    Returns:
        List of entries with updated analysis

    Raises:
        ValueError: If entries is empty
    """
    if not entries:
        msg = "Entries list cannot be empty"
        raise ValueError(msg)

    tasks = []
    for entry in entries:
        if not entry.sentiment or not entry.themes:
            tasks.append(_analyze_single_entry(entry))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=entry)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyzed_entries = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Failed to analyze entry %s: %s", entries[i].id, result)
            analyzed_entries.append(entries[i])
        else:
            analyzed_entries.append(result)

    logger.info("Analyzed %d/%d entries", len(analyzed_entries), len(entries))
    return analyzed_entries


async def _analyze_single_entry(entry: JournalEntry) -> JournalEntry:
    """Analyze single entry for sentiment and themes.

    Args:
        entry: Entry to analyze

    Returns:
        Entry with updated sentiment and themes
    """
    sentiment = await analyze_sentiment(entry.content)
    themes = await extract_themes(entry.content)

    entry.sentiment = sentiment
    entry.themes = [t.name for t in themes]

    return entry


def _fallback_sentiment_detection(text: str) -> str:
    """Keyword-based sentiment detection as fallback.
    
    Used when AI response is unclear or invalid.
    
    Args:
        text: Journal entry text
        
    Returns:
        Sentiment label based on keyword matching
    """
    text_lower = text.lower()
    
    positive_keywords = [
        "happy", "great", "good", "wonderful", "excellent", "amazing",
        "fantastic", "excited", "joy", "love", "grateful", "thankful",
        "accomplished", "success", "proud", "breakthrough", "energized",
        "hopeful", "optimistic", "pleased", "satisfied", "delighted"
    ]
    
    negative_keywords = [
        "sad", "terrible", "awful", "bad", "hate", "angry", "frustrated",
        "disappointed", "upset", "depressed", "anxious", "stressed", "worried",
        "failed", "failure", "wrong", "horrible", "miserable", "unhappy",
        "difficult", "hard", "struggle", "pain", "hurt"
    ]
    
    pos_count = sum(1 for word in positive_keywords if word in text_lower)
    neg_count = sum(1 for word in negative_keywords if word in text_lower)
    
    if pos_count > neg_count and pos_count > 0:
        return "positive"
    elif neg_count > pos_count and neg_count > 0:
        return "negative"
    else:
        return "neutral"
