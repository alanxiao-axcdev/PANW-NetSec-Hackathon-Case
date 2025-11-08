"""Tests for data models."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from companion.models import (
    AnalysisResult,
    Config,
    HealthStatus,
    InjectionRisk,
    JournalEntry,
    PIIMatch,
    PoisoningRisk,
    ProviderHealth,
    Sentiment,
    Summary,
    Theme,
)


class TestSentiment:
    """Test Sentiment model."""

    def test_valid_sentiment(self):
        """Test creating valid sentiment."""
        sentiment = Sentiment(label="positive", confidence=0.85)
        assert sentiment.label == "positive"
        assert sentiment.confidence == 0.85

    def test_all_labels(self):
        """Test all valid sentiment labels."""
        for label in ["positive", "neutral", "negative"]:
            sentiment = Sentiment(label=label, confidence=0.5)
            assert sentiment.label == label

    def test_confidence_bounds(self):
        """Test confidence must be 0-1."""
        # Valid
        Sentiment(label="positive", confidence=0.0)
        Sentiment(label="positive", confidence=1.0)

        # Invalid
        with pytest.raises(ValidationError):
            Sentiment(label="positive", confidence=1.5)
        with pytest.raises(ValidationError):
            Sentiment(label="positive", confidence=-0.1)

    def test_invalid_label(self):
        """Test invalid sentiment label."""
        with pytest.raises(ValidationError):
            Sentiment(label="happy", confidence=0.5)

    def test_immutable(self):
        """Test sentiment is immutable."""
        sentiment = Sentiment(label="positive", confidence=0.8)
        with pytest.raises(ValidationError):
            sentiment.label = "negative"


class TestTheme:
    """Test Theme model."""

    def test_valid_theme(self):
        """Test creating valid theme."""
        theme = Theme(name="work", confidence=0.75)
        assert theme.name == "work"
        assert theme.confidence == 0.75

    def test_confidence_validation(self):
        """Test confidence bounds."""
        with pytest.raises(ValidationError):
            Theme(name="work", confidence=1.2)


class TestJournalEntry:
    """Test JournalEntry model."""

    def test_minimal_entry(self):
        """Test creating entry with minimal data."""
        entry = JournalEntry(content="Test entry")
        assert entry.content == "Test entry"
        assert entry.id  # Should have UUID
        assert entry.timestamp  # Should have timestamp

    def test_full_entry(self):
        """Test entry with all fields."""
        sentiment = Sentiment(label="positive", confidence=0.9)
        entry = JournalEntry(
            content="Great day today!",
            prompt_used="How was your day?",
            sentiment=sentiment,
            themes=["work", "happiness"],
            duration_seconds=120,
            next_session_prompts=["What made it great?"],
            analysis_complete=True,
        )
        assert entry.sentiment == sentiment
        assert "work" in entry.themes
        assert entry.analysis_complete

    def test_default_values(self):
        """Test default field values."""
        entry = JournalEntry(content="Test")
        assert entry.prompt_used is None
        assert entry.sentiment is None
        assert entry.themes == []
        assert entry.next_session_prompts == []
        assert entry.analysis_complete is False

    def test_serialization(self):
        """Test JSON serialization."""
        entry = JournalEntry(content="Test")
        data = entry.model_dump()
        assert data["content"] == "Test"
        assert "id" in data
        assert "timestamp" in data


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_minimal_analysis(self):
        """Test minimal analysis result."""
        sentiment = Sentiment(label="neutral", confidence=0.5)
        theme = Theme(name="general", confidence=0.6)

        result = AnalysisResult(
            entry_id="test-123",
            sentiment=sentiment,
            themes=[theme],
        )
        assert result.entry_id == "test-123"
        assert result.sentiment == sentiment
        assert len(result.themes) == 1

    def test_full_analysis(self):
        """Test complete analysis result."""
        sentiment = Sentiment(label="positive", confidence=0.85)
        themes = [
            Theme(name="work", confidence=0.9),
            Theme(name="achievement", confidence=0.75),
        ]

        result = AnalysisResult(
            entry_id="test-456",
            sentiment=sentiment,
            themes=themes,
            suggested_followup_prompts=["What's next?", "How do you feel?"],
            patterns_detected=["morning_productivity", "project_completion"],
        )
        assert len(result.suggested_followup_prompts) == 2
        assert "morning_productivity" in result.patterns_detected


class TestSummary:
    """Test Summary model."""

    def test_weekly_summary(self):
        """Test weekly summary creation."""
        today = date.today()
        week_ago = today - timedelta(days=7)

        summary = Summary(
            period="week",
            start_date=week_ago,
            end_date=today,
            entry_count=5,
            dominant_themes=["work", "exercise"],
            emotional_trend="Trending positive with high energy",
            insights=[
                "You wrote more on days with morning exercise",
                "Work stress lowest on Fridays",
            ],
        )
        assert summary.period == "week"
        assert summary.entry_count == 5
        assert len(summary.insights) == 2

    def test_monthly_summary(self):
        """Test monthly summary creation."""
        summary = Summary(
            period="month",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            entry_count=20,
        )
        assert summary.period == "month"
        assert summary.entry_count == 20


class TestConfig:
    """Test Config model."""

    def test_default_config(self):
        """Test config with defaults."""
        config = Config()
        assert config.data_directory == Path.home() / ".companion"
        assert config.model_name == "Qwen/Qwen2.5-1.5B"
        assert config.max_prompt_tokens == 100
        assert config.max_summary_tokens == 500
        assert config.first_run_complete is False
        assert config.enable_encryption is True
        assert config.enable_pii_detection is True

    def test_custom_config(self):
        """Test config with custom values."""
        custom_dir = Path("/tmp/test_companion")
        config = Config(
            data_directory=custom_dir,
            model_name="custom/model",
            max_prompt_tokens=200,
            first_run_complete=True,
            enable_encryption=False,
        )
        assert config.data_directory == custom_dir
        assert config.model_name == "custom/model"
        assert config.enable_encryption is False

    def test_serialization(self):
        """Test config can be serialized."""
        config = Config()
        data = config.model_dump()
        assert "data_directory" in data
        assert "model_name" in data


class TestSecurityModels:
    """Test security-related models."""

    def test_pii_match(self):
        """Test PIIMatch model."""
        match = PIIMatch(
            type="email",
            value="test@example.com",
            start=0,
            end=17,
            confidence=0.99,
        )
        assert match.type == "email"
        assert match.confidence == 0.99

    def test_injection_risk(self):
        """Test InjectionRisk model."""
        risk = InjectionRisk(
            level="HIGH",
            score=0.92,
            patterns_detected=["ignore_instructions", "role_confusion"],
            recommended_action="Sanitize before using in prompts",
        )
        assert risk.level == "HIGH"
        assert len(risk.patterns_detected) == 2

    def test_poisoning_risk(self):
        """Test PoisoningRisk model."""
        risk = PoisoningRisk(
            level="MEDIUM",
            score=0.65,
            indicators={"instruction_density": 0.35, "embedding_distance": 0.72},
            entry_id="entry-789",
        )
        assert risk.level == "MEDIUM"
        assert "instruction_density" in risk.indicators


class TestMonitoringModels:
    """Test monitoring-related models."""

    def test_health_status(self):
        """Test HealthStatus model."""
        status = HealthStatus(
            component="model",
            status="OK",
            message="Model loaded and responsive",
        )
        assert status.component == "model"
        assert status.status == "OK"
        assert status.checked_at  # Should have timestamp

    def test_health_status_degraded(self):
        """Test degraded health status."""
        status = HealthStatus(
            component="storage",
            status="DEGRADED",
            message="Low disk space: 2GB remaining",
        )
        assert status.status == "DEGRADED"

    def test_provider_health(self):
        """Test ProviderHealth model."""
        health = ProviderHealth(
            provider_name="qwen",
            is_initialized=True,
            model_loaded=True,
            last_inference_time=245.5,
            error_count=0,
        )
        assert health.provider_name == "qwen"
        assert health.is_initialized
        assert health.last_inference_time == 245.5
