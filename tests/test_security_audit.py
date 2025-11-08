"""Tests for security audit logging."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.security.audit import (
    SecurityAuditLog,
    generate_audit_report,
    log_data_access,
    log_model_inference,
    log_security_event,
)


@pytest.fixture
def temp_audit_log():
    """Create temporary audit log for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_path = Path(f.name)

    audit_log = SecurityAuditLog(log_path=log_path)

    yield audit_log

    # Cleanup
    if log_path.exists():
        log_path.unlink()


class TestSecurityAuditLog:
    """Test SecurityAuditLog class."""

    def test_creates_log_file(self):
        """Should create log file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            audit_log = SecurityAuditLog(log_path=log_path)

            assert log_path.exists()
            assert audit_log.log_path == log_path

    def test_log_model_inference(self, temp_audit_log):
        """Should log model inference event."""
        temp_audit_log.log_model_inference(
            prompt_hash="abc123",
            output_hash="def456",
            duration_ms=150.5,
            model_name="test-model",
        )

        # Read log file
        with temp_audit_log.log_path.open() as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "model_inference"
        assert entry["prompt_hash"] == "abc123"
        assert entry["output_hash"] == "def456"
        assert entry["duration_ms"] == 150.5
        assert entry["model_name"] == "test-model"
        assert "timestamp" in entry

    def test_log_data_access(self, temp_audit_log):
        """Should log data access event."""
        temp_audit_log.log_data_access(
            operation="read",
            entry_ids=["entry-1", "entry-2"],
            user_id="test_user",
        )

        with temp_audit_log.log_path.open() as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "data_access"
        assert entry["operation"] == "read"
        assert entry["entry_count"] == 2
        assert entry["entry_ids"] == ["entry-1", "entry-2"]
        assert entry["user_id"] == "test_user"

    def test_log_security_event(self, temp_audit_log):
        """Should log security event."""
        temp_audit_log.log_security_event(
            event_type="encryption",
            severity="info",
            details={"action": "passphrase_changed"},
        )

        with temp_audit_log.log_path.open() as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "security_event"
        assert entry["subtype"] == "encryption"
        assert entry["severity"] == "info"
        assert entry["details"] == {"action": "passphrase_changed"}

    def test_read_entries_all(self, temp_audit_log):
        """Should read all entries."""
        temp_audit_log.log_model_inference("hash1", "hash2", 100.0)
        temp_audit_log.log_data_access("read", ["id1"])

        entries = temp_audit_log.read_entries()
        assert len(entries) == 2

    def test_read_entries_by_type(self, temp_audit_log):
        """Should filter by event type."""
        temp_audit_log.log_model_inference("hash1", "hash2", 100.0)
        temp_audit_log.log_data_access("read", ["id1"])

        entries = temp_audit_log.read_entries(event_type="model_inference")
        assert len(entries) == 1
        assert entries[0]["event_type"] == "model_inference"

    def test_read_entries_by_date_range(self, temp_audit_log):
        """Should filter by date range."""
        temp_audit_log.log_model_inference("hash1", "hash2", 100.0)

        today = datetime.now(tz=UTC).date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Should include today's entries
        entries = temp_audit_log.read_entries(start_date=yesterday, end_date=tomorrow)
        assert len(entries) == 1

        # Should exclude if outside range
        entries = temp_audit_log.read_entries(start_date=yesterday, end_date=yesterday)
        assert len(entries) == 0

    def test_multiple_entries(self, temp_audit_log):
        """Should handle multiple entries."""
        for i in range(5):
            temp_audit_log.log_model_inference(f"hash{i}", f"out{i}", 100.0 + i)

        entries = temp_audit_log.read_entries()
        assert len(entries) == 5

        # Check durations are correct
        durations = [e["duration_ms"] for e in entries]
        assert durations == [100.0, 101.0, 102.0, 103.0, 104.0]

    def test_read_empty_log(self, temp_audit_log):
        """Should handle empty log file."""
        entries = temp_audit_log.read_entries()
        assert entries == []

    def test_invalid_json_entry(self, temp_audit_log):
        """Should skip invalid JSON entries."""
        # Write invalid JSON
        with temp_audit_log.log_path.open("a") as f:
            f.write("invalid json\n")
            f.write('{"valid": "json"}\n')

        # Should skip invalid, return valid (though it doesn't match event_type filter)
        entries = temp_audit_log.read_entries()
        assert len(entries) == 0  # valid entry has no event_type


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_log_model_inference_function(self, temp_audit_log):
        """Should log using convenience function."""
        log_model_inference(
            prompt="How are you?",
            output="I'm good",
            duration_ms=123.4,
            model_name="test-model",
            audit_log=temp_audit_log,
        )

        entries = temp_audit_log.read_entries()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "model_inference"
        assert entries[0]["duration_ms"] == 123.4

        # Should have hashed content
        assert "prompt_hash" in entries[0]
        assert "output_hash" in entries[0]
        assert len(entries[0]["prompt_hash"]) == 64  # SHA256 hex length

    def test_log_data_access_function(self, temp_audit_log):
        """Should log using convenience function."""
        log_data_access(
            operation="write",
            entry_ids=["id1", "id2"],
            audit_log=temp_audit_log,
        )

        entries = temp_audit_log.read_entries()
        assert len(entries) == 1
        assert entries[0]["operation"] == "write"

    def test_log_security_event_function(self, temp_audit_log):
        """Should log using convenience function."""
        log_security_event(
            event_type="auth",
            details={"user": "test"},
            severity="warning",
            audit_log=temp_audit_log,
        )

        entries = temp_audit_log.read_entries()
        assert len(entries) == 1
        assert entries[0]["severity"] == "warning"


class TestAuditReport:
    """Test audit report generation."""

    def test_generate_report_empty(self, temp_audit_log):
        """Should generate report for empty log."""
        today = datetime.now(tz=UTC).date()
        report = generate_audit_report(
            start_date=today,
            end_date=today,
            audit_log=temp_audit_log,
        )

        assert report["total_events"] == 0
        assert report["event_counts"] == {}
        assert report["total_inference_time_ms"] == 0

    def test_generate_report_with_events(self, temp_audit_log):
        """Should aggregate events in report."""
        temp_audit_log.log_model_inference("h1", "h2", 100.0)
        temp_audit_log.log_model_inference("h3", "h4", 200.0)
        temp_audit_log.log_data_access("read", ["id1"])

        today = datetime.now(tz=UTC).date()
        report = generate_audit_report(
            start_date=today,
            end_date=today,
            audit_log=temp_audit_log,
        )

        assert report["total_events"] == 3
        assert report["event_counts"]["model_inference"] == 2
        assert report["event_counts"]["data_access"] == 1
        assert report["total_inference_time_ms"] == 300.0

    def test_generate_report_date_range(self, temp_audit_log):
        """Should respect date range in report."""
        temp_audit_log.log_model_inference("h1", "h2", 100.0)

        today = datetime.now(tz=UTC).date()
        yesterday = today - timedelta(days=1)

        # Yesterday should have no events
        report = generate_audit_report(
            start_date=yesterday,
            end_date=yesterday,
            audit_log=temp_audit_log,
        )
        assert report["total_events"] == 0

        # Today should have events
        report = generate_audit_report(
            start_date=today,
            end_date=today,
            audit_log=temp_audit_log,
        )
        assert report["total_events"] == 1
