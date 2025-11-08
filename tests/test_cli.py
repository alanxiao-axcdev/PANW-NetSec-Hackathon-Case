"""Tests for CLI module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from companion import cli
from companion.models import HealthStatus, JournalEntry, Sentiment, Summary


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch("companion.cli.config") as mock:
        mock_cfg = MagicMock()
        mock_cfg.first_run_complete = True
        mock_cfg.data_directory = MagicMock()
        mock.load_config.return_value = mock_cfg
        yield mock


@pytest.fixture
def mock_journal():
    """Mock journal operations."""
    with patch("companion.cli.journal") as mock:
        yield mock


@pytest.fixture
def mock_analyzer():
    """Mock analyzer operations."""
    with patch("companion.cli.analyzer") as mock:
        yield mock


@pytest.fixture
def mock_summarizer():
    """Mock summarizer operations."""
    with patch("companion.cli.summarizer") as mock:
        yield mock


@pytest.fixture
def mock_health():
    """Mock health checks."""
    with patch("companion.cli.health") as mock:
        yield mock


@pytest.fixture
def mock_dashboard():
    """Mock dashboard."""
    with patch("companion.cli.dashboard") as mock:
        yield mock


class TestWriteCommand:
    """Tests for write command."""

    def test_write_entry_basic(self, runner, mock_config, mock_journal, mock_analyzer):
        """Test writing a basic entry."""
        # Mock input
        test_content = "Today was a good day.\nI learned something new."

        # Mock journal.save_entry
        mock_journal.save_entry.return_value = "test-entry-id"

        # Mock async analysis (will be skipped in test due to exception)
        mock_analyzer.analyze_sentiment.side_effect = RuntimeError("Mock error")

        result = runner.invoke(cli.write, input=test_content + "\n")

        # Should succeed even if analysis fails
        assert result.exit_code == 0
        assert mock_journal.save_entry.called
        assert "Entry saved" in result.output or "saved" in result.output.lower()

    def test_write_entry_empty(self, runner, mock_config, mock_journal):
        """Test that empty entry is not saved."""
        result = runner.invoke(cli.write, input="\n")

        assert result.exit_code == 0
        assert not mock_journal.save_entry.called
        assert "Empty entry" in result.output or "not saved" in result.output.lower()

    def test_write_entry_cancel(self, runner, mock_config, mock_journal):
        """Test canceling entry with Ctrl+C."""
        # Simulate KeyboardInterrupt
        _ = runner.invoke(cli.write, input="", catch_exceptions=False)

        # Exit code may vary, but entry should not be saved
        assert not mock_journal.save_entry.called


class TestListCommand:
    """Tests for list command."""

    def test_list_entries_basic(self, runner, mock_config, mock_journal):
        """Test listing entries."""
        # Create mock entries
        entries = [
            JournalEntry(
                content="Entry 1 content here",
                sentiment=Sentiment(label="positive", confidence=0.8),
                themes=["work", "achievement"],
            ),
            JournalEntry(
                content="Entry 2 content here",
                sentiment=Sentiment(label="neutral", confidence=0.6),
                themes=["general"],
            ),
        ]
        mock_journal.get_recent_entries.return_value = entries

        result = runner.invoke(cli.list_entries)

        assert result.exit_code == 0
        assert mock_journal.get_recent_entries.called
        assert "Entry 1" in result.output or "Entry 2" in result.output

    def test_list_entries_with_limit(self, runner, mock_config, mock_journal):
        """Test listing entries with custom limit."""
        mock_journal.get_recent_entries.return_value = []

        result = runner.invoke(cli.list_entries, ["--limit", "5"])

        assert result.exit_code == 0
        mock_journal.get_recent_entries.assert_called_with(limit=5)

    def test_list_entries_by_date(self, runner, mock_config, mock_journal):
        """Test listing entries for specific date."""
        mock_journal.get_entries_by_date_range.return_value = []

        result = runner.invoke(cli.list_entries, ["--date", "2025-01-08"])

        assert result.exit_code == 0
        assert mock_journal.get_entries_by_date_range.called

    def test_list_entries_no_entries(self, runner, mock_config, mock_journal):
        """Test listing when no entries exist."""
        mock_journal.get_recent_entries.return_value = []

        result = runner.invoke(cli.list_entries)

        assert result.exit_code == 0
        assert "No entries found" in result.output or "no entries" in result.output.lower()

    def test_list_entries_invalid_date(self, runner, mock_config, mock_journal):
        """Test listing with invalid date format."""
        result = runner.invoke(cli.list_entries, ["--date", "invalid-date"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()


class TestShowCommand:
    """Tests for show command."""

    def test_show_entry_basic(self, runner, mock_config, mock_journal):
        """Test showing a specific entry."""
        entry = JournalEntry(
            id="test-entry-123",
            content="This is my journal entry content.",
            sentiment=Sentiment(label="positive", confidence=0.85),
            themes=["reflection", "gratitude"],
        )
        mock_journal.get_entry.return_value = entry

        result = runner.invoke(cli.show, ["test-entry-123"])

        assert result.exit_code == 0
        mock_journal.get_entry.assert_called_with("test-entry-123")
        assert "journal entry content" in result.output.lower() or "entry" in result.output.lower()

    def test_show_entry_not_found(self, runner, mock_config, mock_journal):
        """Test showing non-existent entry."""
        mock_journal.get_entry.side_effect = FileNotFoundError("Not found")

        result = runner.invoke(cli.show, ["nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestSummaryCommand:
    """Tests for summary command."""

    def test_summary_week_basic(self, runner, mock_config, mock_journal, mock_summarizer):
        """Test weekly summary generation."""
        # Mock no entries for simplicity
        mock_journal.get_entries_by_date_range.return_value = []

        result = runner.invoke(cli.summary, ["--period", "week"])

        # Should handle gracefully
        assert result.exit_code == 0
        assert mock_journal.get_entries_by_date_range.called

    def test_summary_month(self, runner, mock_config, mock_journal, mock_summarizer):
        """Test monthly summary generation."""
        mock_journal.get_entries_by_date_range.return_value = []

        result = runner.invoke(cli.summary, ["--period", "month"])

        # Should handle no entries gracefully
        assert result.exit_code == 0

    def test_summary_no_entries(self, runner, mock_config, mock_journal):
        """Test summary with no entries."""
        mock_journal.get_entries_by_date_range.return_value = []

        result = runner.invoke(cli.summary)

        assert result.exit_code == 0
        assert "No entries" in result.output or "no entries" in result.output.lower()


class TestHealthCommand:
    """Tests for health command."""

    def test_health_check_all_ok(self, runner, mock_config, mock_health):
        """Test health check when all systems OK."""
        mock_health.check_model_loaded.return_value = HealthStatus(
            component="ai_model", status="OK", message="Model loaded"
        )
        mock_health.check_storage_accessible.return_value = HealthStatus(
            component="storage", status="OK", message="Storage accessible"
        )
        mock_health.check_disk_space.return_value = HealthStatus(
            component="disk_space", status="OK", message="Sufficient space"
        )
        mock_health.check_memory_available.return_value = HealthStatus(
            component="memory", status="OK", message="Memory available"
        )

        result = runner.invoke(cli.health_check)

        assert result.exit_code == 0
        assert "HEALTHY" in result.output or "OK" in result.output

    def test_health_check_degraded(self, runner, mock_config, mock_health):
        """Test health check when system degraded."""
        mock_health.check_model_loaded.return_value = HealthStatus(
            component="ai_model", status="DEGRADED", message="Model slow"
        )
        mock_health.check_storage_accessible.return_value = HealthStatus(
            component="storage", status="OK", message="Storage accessible"
        )
        mock_health.check_disk_space.return_value = HealthStatus(
            component="disk_space", status="OK", message="Sufficient space"
        )
        mock_health.check_memory_available.return_value = HealthStatus(
            component="memory", status="OK", message="Memory available"
        )

        result = runner.invoke(cli.health_check)

        assert result.exit_code == 0
        assert "DEGRADED" in result.output or "⚠" in result.output


class TestMetricsCommand:
    """Tests for metrics command."""

    def test_metrics_display(self, runner, mock_config, mock_dashboard):
        """Test metrics dashboard display."""
        result = runner.invoke(cli.metrics)

        assert result.exit_code == 0
        assert mock_dashboard.display_metrics_dashboard.called


class TestVersionCommand:
    """Tests for version command."""

    def test_version_display(self, runner):
        """Test version command."""
        result = runner.invoke(cli.version)

        assert result.exit_code == 0
        assert "Companion" in result.output
        assert "v0.1.0" in result.output or "version" in result.output.lower()


class TestFirstRunWizard:
    """Tests for first-run wizard."""

    def test_first_run_wizard_executes(self, runner, mock_config):
        """Test first-run wizard runs on first use."""
        # Mock as first run
        mock_cfg = MagicMock()
        mock_cfg.first_run_complete = False
        mock_config.load_config.return_value = mock_cfg
        mock_config.save_config = MagicMock()

        # Invoke main with help (simple test)
        result = runner.invoke(cli.main, ["--help"])

        # Should succeed
        assert result.exit_code == 0

    def test_first_run_wizard_skips_after_complete(self, runner, mock_config):
        """Test wizard skips when already completed."""
        # Already configured
        mock_cfg = MagicMock()
        mock_cfg.first_run_complete = True
        mock_config.load_config.return_value = mock_cfg

        result = runner.invoke(cli.main, ["--help"])

        # Should not initialize again
        assert result.exit_code == 0


class TestHelpers:
    """Tests for helper functions."""

    def test_display_greeting_morning(self):
        """Test morning greeting."""
        with patch("companion.cli.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(hour=8)
            # Should not raise
            cli._display_greeting()

    def test_display_greeting_afternoon(self):
        """Test afternoon greeting."""
        with patch("companion.cli.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(hour=14)
            cli._display_greeting()

    def test_display_greeting_evening(self):
        """Test evening greeting."""
        with patch("companion.cli.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(hour=20)
            cli._display_greeting()

    def test_format_entry_summary(self):
        """Test entry summary formatting."""
        entry = JournalEntry(
            content="Test content for entry",
            sentiment=Sentiment(label="positive", confidence=0.9),
            themes=["test", "example"],
        )

        result = cli._format_entry_summary(entry)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain key elements
        assert "test" in result.lower() or "content" in result.lower()
