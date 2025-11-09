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

    Sanitizes PII before sending to AI model for privacy protection.

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

    # Security checks before AI processing
    from companion.security.pii_detector import detect_pii
    from companion.security_research.prompt_injection_detector import detect_injection

    # 1. Check for prompt injection attempts
    sanitized_text = text
    try:
        injection_risk = detect_injection(text)
        if injection_risk.level in ["MEDIUM", "HIGH"]:
            logger.warning(
                "Potential prompt injection detected (risk: %s) in analysis input. Patterns: %s",
                injection_risk.level,
                injection_risk.patterns_detected
            )
            # Continue but log for security monitoring
    except Exception as e:
        logger.debug("Prompt injection check failed (non-critical): %s", e)

    # 2. Sanitize PII before sending to AI
    try:
        pii_matches = detect_pii(text)
        if pii_matches:
            # Redact PII for AI analysis (keeps sentiment intact)
            for match in sorted(pii_matches, key=lambda m: m.start, reverse=True):
                # Replace PII with generic placeholder
                placeholder = f"[{match.type}]"
                sanitized_text = sanitized_text[:match.start] + placeholder + sanitized_text[match.end:]
            logger.debug("Sanitized %d PII instances before AI analysis", len(pii_matches))
    except Exception as e:
        logger.debug("PII sanitization failed (non-critical): %s", e)
        # Continue with original text if sanitization fails

    prompt = f"""Analyze the sentiment of this journal entry.

Entry: "{sanitized_text[:500]}"

Respond with ONLY ONE WORD (no explanation, no punctuation):
- positive (if the entry expresses positive emotions)
- neutral (if the entry is factual or balanced)
- negative (if the entry expresses negative emotions)

Your response (one word only):"""

    try:
        from companion.utils.retry import retry_with_backoff

        # Retry Qwen up to 2 times if it fails (fast model, worth retrying)
        async def generate_sentiment():
            return await ai_engine.generate_text(prompt, max_tokens=10)

        response = await retry_with_backoff(generate_sentiment, max_retries=2, base_delay=0.5)
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

    Sanitizes PII before sending to AI model for privacy protection.

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

    # Security checks before AI processing
    from companion.security.pii_detector import detect_pii
    from companion.security_research.prompt_injection_detector import detect_injection

    # 1. Check for prompt injection attempts
    sanitized_text = text
    try:
        injection_risk = detect_injection(text)
        if injection_risk.level in ["MEDIUM", "HIGH"]:
            logger.warning(
                "Potential prompt injection detected (risk: %s) in analysis input. Patterns: %s",
                injection_risk.level,
                injection_risk.patterns_detected
            )
            # Continue but log for security monitoring
    except Exception as e:
        logger.debug("Prompt injection check failed (non-critical): %s", e)

    # 2. Sanitize PII before sending to AI
    try:
        pii_matches = detect_pii(text)
        if pii_matches:
            # Redact PII for AI analysis (preserves themes)
            for match in sorted(pii_matches, key=lambda m: m.start, reverse=True):
                placeholder = f"[{match.type}]"
                sanitized_text = sanitized_text[:match.start] + placeholder + sanitized_text[match.end:]
            logger.debug("Sanitized %d PII instances before AI analysis", len(pii_matches))
    except Exception as e:
        logger.debug("PII sanitization failed (non-critical): %s", e)
        # Continue with original text if sanitization fails

    prompt = f"""Read this journal entry and identify 2-4 main themes or topics.

Entry: "{sanitized_text[:500]}"

List the themes as comma-separated single words (no explanations).

Themes:"""

    try:
        from companion.utils.retry import retry_with_backoff

        # Retry Qwen up to 2 times if it fails (fast model, worth retrying)
        async def generate_themes():
            return await ai_engine.generate_text(prompt, max_tokens=30)

        response = await retry_with_backoff(generate_themes, max_retries=2, base_delay=0.5)

        # Clean response: extract only the comma-separated words
        # Remove any sentences or extra text
        response_clean = response.strip().lower()

        # If response has newlines or periods, take only first line/sentence
        if '\n' in response_clean:
            response_clean = response_clean.split('\n')[0]
        if '.' in response_clean and response_clean.index('.') < 50:
            response_clean = response_clean.split('.')[0]

        # Try to extract themes from response
        theme_names = [t.strip().strip('"\'').rstrip('.') for t in response_clean.split(",") if t.strip()]

        # Filter out common non-theme words that might appear in verbose responses
        exclude_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "a", "an", "is", "are", "was", "were"}
        theme_names = [name for name in theme_names if name not in exclude_words and len(name) > 2]

        # If we didn't get any valid themes, use fallback
        if not theme_names:
            logger.debug("Theme extraction unclear (got 0 themes), using keyword fallback")
            theme_names = _fallback_theme_extraction(text)
        # If too many themes, take the most relevant ones (Qwen lists them in order of relevance)
        elif len(theme_names) > 6:
            logger.debug("Qwen returned %d themes, taking top 4", len(theme_names))
            theme_names = theme_names[:4]
        # If only 1 theme from AI - supplement with keyword detection
        elif len(theme_names) == 1:
            logger.debug("Only 1 theme from AI, supplementing with keywords")
            keyword_themes = _fallback_theme_extraction(text)
            # Add first keyword theme that's different from AI theme
            for kt in keyword_themes:
                if kt not in theme_names:
                    theme_names.append(kt)
                    break

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


def _fallback_theme_extraction(text: str) -> list[str]:
    """Keyword-based theme extraction as fallback.

    Used when AI response is unclear or invalid.

    Args:
        text: Journal entry text

    Returns:
        List of theme names based on keyword matching
    """
    text_lower = text.lower()

    # Define theme categories with their keywords
    theme_keywords = {
        "work": ["work", "job", "career", "office", "project", "meeting", "deadline", "boss", "colleague"],
        "family": ["family", "parent", "child", "spouse", "sibling", "home", "kids", "daughter", "son"],
        "health": ["health", "exercise", "fitness", "doctor", "medical", "pain", "sick", "wellness"],
        "stress": ["stress", "anxiety", "worried", "overwhelmed", "pressure", "tense", "nervous"],
        "relationships": ["friend", "relationship", "social", "partner", "dating", "love", "connection"],
        "personal": ["self", "myself", "personal", "growth", "development", "identity", "purpose"],
        "creativity": ["creative", "art", "music", "writing", "design", "create", "expression"],
        "finance": ["money", "finance", "budget", "savings", "income", "expense", "financial"],
        "learning": ["learn", "study", "education", "course", "knowledge", "skill", "training"],
        "leisure": ["hobby", "fun", "entertainment", "vacation", "relax", "enjoy", "leisure"],
    }

    # Count occurrences of keywords for each theme
    theme_scores = {}
    for theme, keywords in theme_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            theme_scores[theme] = score

    # Get top 2-4 themes by score
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
    theme_names = [theme for theme, score in sorted_themes[:4]]

    # Ensure we have at least 2 themes
    if len(theme_names) < 2:
        theme_names = ["reflection", "thoughts"]

    return theme_names
