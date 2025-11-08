"""Tests for encrypted audit logging functionality.

Verifies encryption, integrity verification, decryption, and tamper detection.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.security.audit import (
    decrypt_audit_log,
    log_event_encrypted,
    verify_audit_log_integrity,
)


@pytest.fixture
def temp_audit_file(tmp_path: Path) -> Path:
    """Create temporary audit log file."""
    return tmp_path / "audit_encrypted.log"


@pytest.fixture
def test_passphrase() -> str:
    """Test passphrase."""
    return "test_secure_passphrase_123"


def test_encrypted_logging(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that events can be logged with encryption."""
    details = {
        "action": "test_action",
        "user": "test_user",
        "resource": "test_resource",
    }

    log_event_encrypted(
        event_type="security_event",
        details=details,
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    assert temp_audit_file.exists()

    # Verify file has content
    content = temp_audit_file.read_text()
    assert len(content) > 0

    # Verify structure (should be JSON with required fields)
    entry = json.loads(content.strip())
    assert "timestamp" in entry
    assert "encrypted_event" in entry
    assert "integrity_hash" in entry


def test_integrity_verification_success(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that integrity verification succeeds for valid logs."""
    # Log some events
    for i in range(3):
        log_event_encrypted(
            event_type="test_event",
            details={"index": i, "data": f"test_data_{i}"},
            passphrase=test_passphrase,
            audit_file=temp_audit_file,
        )

    # Verify integrity
    integrity_ok, tampered = verify_audit_log_integrity(temp_audit_file, test_passphrase)

    assert integrity_ok is True
    assert len(tampered) == 0


def test_decryption_success(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that encrypted events can be decrypted."""
    test_details = {
        "action": "login",
        "user": "testuser",
        "ip": "192.168.1.1",
    }

    log_event_encrypted(
        event_type="security_event",
        details=test_details,
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Decrypt
    events = decrypt_audit_log(temp_audit_file, test_passphrase)

    assert len(events) == 1
    event = events[0]

    assert event["event_type"] == "security_event"
    assert event["action"] == "login"
    assert event["user"] == "testuser"
    assert event["ip"] == "192.168.1.1"
    assert "timestamp" in event


def test_decryption_with_wrong_passphrase(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that decryption fails with wrong passphrase."""
    log_event_encrypted(
        event_type="test_event",
        details={"data": "secret"},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Try to decrypt with wrong passphrase
    events = decrypt_audit_log(temp_audit_file, "wrong_passphrase")

    # Should return empty list (can't decrypt)
    assert len(events) == 0


def test_tampering_detection(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that tampering is detected through integrity verification."""
    # Log an event
    log_event_encrypted(
        event_type="test_event",
        details={"data": "original"},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Verify integrity is OK before tampering
    integrity_ok, _ = verify_audit_log_integrity(temp_audit_file, test_passphrase)
    assert integrity_ok is True

    # Tamper with the file (modify encrypted_event)
    content = temp_audit_file.read_text()
    entry = json.loads(content.strip())

    # Modify the encrypted event (flip a character)
    encrypted = entry["encrypted_event"]
    tampered_encrypted = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")
    entry["encrypted_event"] = tampered_encrypted

    # Write tampered entry back
    temp_audit_file.write_text(json.dumps(entry) + "\n")

    # Verify integrity should now fail
    integrity_ok, tampered = verify_audit_log_integrity(temp_audit_file, test_passphrase)

    assert integrity_ok is False
    assert len(tampered) > 0
    assert "Line 1" in tampered[0]


def test_tampering_detection_multiple_entries(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test tampering detection with multiple entries."""
    # Log multiple events
    for i in range(5):
        log_event_encrypted(
            event_type="test_event",
            details={"index": i},
            passphrase=test_passphrase,
            audit_file=temp_audit_file,
        )

    # Tamper with entry 3 (line 3)
    lines = temp_audit_file.read_text().strip().split("\n")
    entry = json.loads(lines[2])  # Third entry (index 2)

    # Modify encrypted data
    encrypted = entry["encrypted_event"]
    entry["encrypted_event"] = encrypted[:-1] + "X"
    lines[2] = json.dumps(entry)

    # Write back
    temp_audit_file.write_text("\n".join(lines) + "\n")

    # Verify integrity
    integrity_ok, tampered = verify_audit_log_integrity(temp_audit_file, test_passphrase)

    assert integrity_ok is False
    assert len(tampered) == 1
    assert "Line 3" in tampered[0]


def test_date_filtering(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test filtering events by date range."""
    now = datetime.now(tz=UTC)

    # Log events with different timestamps (we'll manually adjust timestamps)
    details_list = [
        {"day": "yesterday", "timestamp": (now - timedelta(days=1)).isoformat()},
        {"day": "today", "timestamp": now.isoformat()},
        {"day": "tomorrow", "timestamp": (now + timedelta(days=1)).isoformat()},
    ]

    for details in details_list:
        log_event_encrypted(
            event_type="test_event",
            details=details,
            passphrase=test_passphrase,
            audit_file=temp_audit_file,
        )

    # Filter to only today and future
    events = decrypt_audit_log(
        temp_audit_file,
        test_passphrase,
        start_date=now,
    )

    # Should get 2 events (today and tomorrow)
    assert len(events) >= 2

    # Filter to only past
    events = decrypt_audit_log(
        temp_audit_file,
        test_passphrase,
        end_date=now - timedelta(hours=1),
    )

    # Should get 1 event (yesterday)
    assert len(events) >= 1


def test_empty_audit_log(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test behavior with empty/non-existent audit log."""
    # Non-existent file
    integrity_ok, tampered = verify_audit_log_integrity(temp_audit_file, test_passphrase)
    assert integrity_ok is True
    assert len(tampered) == 0

    events = decrypt_audit_log(temp_audit_file, test_passphrase)
    assert len(events) == 0


def test_multiple_event_types(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test logging and decrypting different event types."""
    event_types = [
        ("model_inference", {"duration_ms": 245.5, "model_name": "test-model"}),
        ("data_access", {"operation": "read", "entry_ids": ["abc", "def"]}),
        ("security_event", {"subtype": "auth", "severity": "info"}),
    ]

    for event_type, details in event_types:
        log_event_encrypted(
            event_type=event_type,
            details=details,
            passphrase=test_passphrase,
            audit_file=temp_audit_file,
        )

    # Decrypt all
    events = decrypt_audit_log(temp_audit_file, test_passphrase)

    assert len(events) == 3
    assert events[0]["event_type"] == "model_inference"
    assert events[1]["event_type"] == "data_access"
    assert events[2]["event_type"] == "security_event"


def test_append_only_behavior(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test that logging is append-only (doesn't overwrite)."""
    # Log first event
    log_event_encrypted(
        event_type="test_event",
        details={"seq": 1},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Log second event
    log_event_encrypted(
        event_type="test_event",
        details={"seq": 2},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Both events should be present
    events = decrypt_audit_log(temp_audit_file, test_passphrase)
    assert len(events) == 2
    assert events[0]["seq"] == 1
    assert events[1]["seq"] == 2


def test_corrupted_entry_handling(temp_audit_file: Path, test_passphrase: str) -> None:
    """Test handling of corrupted log entries."""
    # Log valid event
    log_event_encrypted(
        event_type="test_event",
        details={"data": "valid"},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Append corrupted entry
    with temp_audit_file.open("a") as f:
        f.write("CORRUPTED DATA\n")

    # Log another valid event
    log_event_encrypted(
        event_type="test_event",
        details={"data": "valid2"},
        passphrase=test_passphrase,
        audit_file=temp_audit_file,
    )

    # Verify integrity should report the corrupted entry
    integrity_ok, tampered = verify_audit_log_integrity(temp_audit_file, test_passphrase)
    assert integrity_ok is False
    assert len(tampered) > 0

    # Decryption should skip corrupted entry but get valid ones
    events = decrypt_audit_log(temp_audit_file, test_passphrase)
    assert len(events) == 2  # Should get the 2 valid entries
