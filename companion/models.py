"""Data models for Companion journaling application.

All data structures using Pydantic for validation and serialization.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Sentiment(BaseModel):
    """Sentiment classification result.

    Attributes:
        label: Sentiment classification (positive, neutral, negative)
        confidence: Confidence score (0.0 to 1.0)
    """

    model_config = ConfigDict(frozen=True)

    label: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0.0, le=1.0)


class Theme(BaseModel):
    """Detected theme in journal entry.

    Attributes:
        name: Theme name (e.g., "work", "relationships", "health")
        confidence: Confidence score (0.0 to 1.0)
    """

    model_config = ConfigDict(frozen=True)

    name: str
    confidence: float = Field(ge=0.0, le=1.0)


class JournalEntry(BaseModel):
    """Single journal entry with metadata and analysis.

    Attributes:
        id: Unique identifier
        timestamp: When entry was created
        content: User's journal text
        prompt_used: The AI prompt that was shown (if any)
        sentiment: Sentiment analysis result
        themes: Extracted themes
        word_count: Number of words in entry
        duration_seconds: How long user spent writing
        next_session_prompts: AI-generated prompts for next session
        analysis_complete: Whether post-session analysis finished
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    prompt_used: str | None = None
    sentiment: Sentiment | None = None
    themes: list[str] = Field(default_factory=list)
    word_count: int = 0
    duration_seconds: int = 0
    next_session_prompts: list[str] = Field(default_factory=list)
    analysis_complete: bool = False

    def __init__(self, **data):
        """Initialize entry and calculate word count."""
        super().__init__(**data)
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())


class AnalysisResult(BaseModel):
    """Results from post-session analysis.

    Attributes:
        entry_id: ID of analyzed entry
        sentiment: Detected sentiment
        themes: Extracted themes with confidence scores
        suggested_followup_prompts: Prompts for next session
        patterns_detected: Recurring patterns identified
        created_at: When analysis was performed
    """

    entry_id: str
    sentiment: Sentiment
    themes: list[Theme]
    suggested_followup_prompts: list[str] = Field(default_factory=list)
    patterns_detected: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class Summary(BaseModel):
    """Weekly or monthly journal summary.

    Attributes:
        period: Summary period (week or month)
        start_date: Period start date
        end_date: Period end date
        entry_count: Number of entries in period
        dominant_themes: Most common themes
        emotional_trend: Human-readable emotion description
        insights: AI-generated insights
        generated_at: When summary was created
    """

    period: Literal["week", "month"]
    start_date: date
    end_date: date
    entry_count: int
    dominant_themes: list[str] = Field(default_factory=list)
    emotional_trend: str = ""
    insights: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


class Config(BaseModel):
    """Application configuration.

    Attributes:
        data_directory: Where journal data is stored
        model_name: Hugging Face model identifier
        max_prompt_tokens: Maximum tokens for prompt generation
        max_summary_tokens: Maximum tokens for summary generation
        first_run_complete: Whether initial setup is done
        enable_encryption: Whether to encrypt entries
        enable_pii_detection: Whether to detect PII
        enable_audit_logging: Whether to log security events
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data_directory: Path = Field(default=Path.home() / ".companion")
    model_name: str = "Qwen/Qwen2.5-1.5B"
    max_prompt_tokens: int = 100
    max_summary_tokens: int = 500
    first_run_complete: bool = False
    enable_encryption: bool = True
    enable_pii_detection: bool = True
    enable_audit_logging: bool = True


# Security-related models

class PIIMatch(BaseModel):
    """Detected PII in text.

    Attributes:
        type: Type of PII (SSN, email, phone, etc.)
        value: Detected value
        start: Start position in text
        end: End position in text
        confidence: Detection confidence (0.0 to 1.0)
    """

    type: str
    value: str
    start: int
    end: int
    confidence: float = Field(ge=0.0, le=1.0)


class InjectionRisk(BaseModel):
    """Prompt injection risk assessment.

    Attributes:
        level: Risk level (LOW, MEDIUM, HIGH)
        score: Risk score (0.0 to 1.0)
        patterns_detected: Specific patterns found
        recommended_action: What to do about it
    """

    level: Literal["LOW", "MEDIUM", "HIGH"]
    score: float = Field(ge=0.0, le=1.0)
    patterns_detected: list[str] = Field(default_factory=list)
    recommended_action: str = ""


class PoisoningRisk(BaseModel):
    """Data poisoning risk assessment.

    Attributes:
        level: Risk level (LOW, MEDIUM, HIGH)
        score: Risk score (0.0 to 1.0)
        indicators: Specific indicators detected
        entry_id: ID of suspicious entry
    """

    level: Literal["LOW", "MEDIUM", "HIGH"]
    score: float = Field(ge=0.0, le=1.0)
    indicators: dict[str, float] = Field(default_factory=dict)
    entry_id: str = ""


class HealthStatus(BaseModel):
    """Health check result.

    Attributes:
        component: Component being checked
        status: Health status (OK, DEGRADED, DOWN)
        message: Status description
        checked_at: When check was performed
    """

    component: str
    status: Literal["OK", "DEGRADED", "DOWN"]
    message: str = ""
    checked_at: datetime = Field(default_factory=datetime.now)


class ProviderHealth(BaseModel):
    """AI provider health status.

    Attributes:
        provider_name: Name of the provider
        is_initialized: Whether provider is ready
        model_loaded: Whether model is loaded in memory
        last_inference_time: Duration of last inference (ms)
        error_count: Number of recent errors
    """

    provider_name: str
    is_initialized: bool = False
    model_loaded: bool = False
    last_inference_time: float | None = None
    error_count: int = 0


class RotationMetadata(BaseModel):
    """Key rotation metadata.

    Attributes:
        last_rotation: When keys were last rotated
        rotation_interval_days: Days between rotations
        next_rotation_due: When next rotation is due
        total_rotations: Count of rotations performed
    """

    last_rotation: datetime
    rotation_interval_days: int = 90
    next_rotation_due: datetime
    total_rotations: int = 0


class RotationResult(BaseModel):
    """Result of key rotation operation.

    Attributes:
        success: Whether rotation succeeded
        entries_rotated: Number of entries re-encrypted
        entries_failed: Number that failed
        errors: List of errors encountered
        duration_seconds: How long rotation took
    """

    success: bool
    entries_rotated: int
    entries_failed: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
