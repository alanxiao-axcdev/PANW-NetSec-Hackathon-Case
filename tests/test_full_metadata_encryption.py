"""Tests for full entry metadata encryption."""

import json
import tempfile
from pathlib import Path

import pytest

from companion import journal
from companion.models import JournalEntry, Sentiment


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Create temporary data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        from companion.models import Config

        config = Config(data_directory=temp_path, enable_encryption=True)

        def mock_load_config():
            return config

        monkeypatch.setattr("companion.journal.load_config", mock_load_config)
        monkeypatch.setattr("companion.config.load_config", mock_load_config)

        yield temp_path


TEST_PASSPHRASE = "test-secure-passphrase-2025!"


def test_full_metadata_encryption_no_plaintext_leak(temp_data_dir):
    """Test that NO metadata is stored in plaintext (critical security check)."""
    entry = JournalEntry(
        content="Secret journal entry",
        sentiment=Sentiment(label="positive", confidence=0.95),
        themes=["work", "health", "relationships"],
        next_session_prompts=["How are you feeling?", "What's on your mind?"],
        duration_seconds=120,
    )

    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    # Read raw file
    entries_dir = temp_data_dir / "entries"
    entry_file = entries_dir / f"{entry_id}.json"

    with open(entry_file) as f:
        raw_content = f.read()
        raw_data = json.loads(raw_content)

    # CRITICAL: Verify NO plaintext leaks
    assert "Secret journal entry" not in raw_content, "Content leaked in plaintext!"
    assert "positive" not in raw_content, "Sentiment leaked in plaintext!"
    assert "work" not in raw_content, "Themes leaked in plaintext!"
    assert "health" not in raw_content, "Themes leaked in plaintext!"
    assert "How are you feeling?" not in raw_content, "Prompts leaked in plaintext!"

    # Verify ONLY safe fields are present
    assert set(raw_data.keys()) == {"id", "encrypted", "salt", "nonce", "ciphertext"}
    assert raw_data["encrypted"] is True
    assert raw_data["id"] == entry_id

    # Verify encryption metadata is present
    assert "salt" in raw_data
    assert "nonce" in raw_data
    assert "ciphertext" in raw_data


def test_full_entry_decryption_restores_all_metadata(temp_data_dir):
    """Test that decryption restores ALL fields correctly."""
    original = JournalEntry(
        content="Private thoughts",
        sentiment=Sentiment(label="neutral", confidence=0.8),
        themes=["family", "career"],
        next_session_prompts=["Tell me more"],
        duration_seconds=300,
    )

    entry_id = journal.save_entry(original, passphrase=TEST_PASSPHRASE)
    retrieved = journal.get_entry(entry_id, passphrase=TEST_PASSPHRASE)

    assert retrieved is not None
    assert retrieved.id == original.id
    assert retrieved.content == "Private thoughts"
    assert retrieved.sentiment.label == "neutral"
    assert retrieved.sentiment.confidence == 0.8
    assert retrieved.themes == ["family", "career"]
    assert retrieved.next_session_prompts == ["Tell me more"]
    assert retrieved.duration_seconds == 300
    assert retrieved.timestamp == original.timestamp


def test_backward_compatibility_with_legacy_content_only_encryption(temp_data_dir):
    """Test that old content-only encrypted entries can still be read."""
    # Simulate legacy entry format (only content encrypted, metadata plaintext)
    from companion.security.encryption import encrypt_entry_to_dict

    entry = JournalEntry(
        content="Legacy entry",
        sentiment=Sentiment(label="positive", confidence=0.9),
        themes=["legacy"],
    )

    # Create LEGACY format (content-only encryption)
    encrypted_content = encrypt_entry_to_dict(entry.content, TEST_PASSPHRASE)

    legacy_entry_dict = {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "encrypted": True,
        "salt": encrypted_content["salt"],
        "nonce": encrypted_content["nonce"],
        "ciphertext": encrypted_content["ciphertext"],
        "sentiment": entry.sentiment.model_dump(mode="json"),  # PLAINTEXT (legacy)
        "themes": entry.themes,  # PLAINTEXT (legacy)
        "next_session_prompts": entry.next_session_prompts,
        "duration_seconds": entry.duration_seconds,
    }

    # Write legacy format to file
    entries_dir = temp_data_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    legacy_file = entries_dir / f"{entry.id}.json"

    with open(legacy_file, "w") as f:
        json.dump(legacy_entry_dict, f)

    # Should be able to read legacy entry
    retrieved = journal.get_entry(entry.id, passphrase=TEST_PASSPHRASE)

    assert retrieved is not None
    assert retrieved.id == entry.id
    assert retrieved.content == "Legacy entry"
    assert retrieved.sentiment.label == "positive"
    assert retrieved.themes == ["legacy"]


def test_get_recent_entries_with_full_encryption(temp_data_dir):
    """Test getting recent entries with full metadata encryption."""
    entries = []
    for i in range(3):
        entry = JournalEntry(
            content=f"Entry {i}",
            sentiment=Sentiment(label="positive", confidence=0.9),
            themes=[f"theme-{i}"],
        )
        entries.append(entry)
        journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    recent = journal.get_recent_entries(limit=2, passphrase=TEST_PASSPHRASE)

    assert len(recent) == 2
    # Verify metadata is restored
    assert all(e.sentiment is not None for e in recent)
    assert all(len(e.themes) > 0 for e in recent)


def test_search_with_full_encryption(temp_data_dir):
    """Test search works with full metadata encryption."""
    entry1 = JournalEntry(content="Meeting with team", themes=["work"])
    entry2 = JournalEntry(content="Gym session", themes=["health"])

    journal.save_entry(entry1, passphrase=TEST_PASSPHRASE)
    journal.save_entry(entry2, passphrase=TEST_PASSPHRASE)

    results = journal.search_entries("team", passphrase=TEST_PASSPHRASE)

    assert len(results) == 1
    assert "team" in results[0].content.lower()
    assert results[0].themes == ["work"]


def test_wrong_passphrase_fails_on_full_encryption(temp_data_dir):
    """Test that wrong passphrase fails to decrypt full entry."""
    entry = JournalEntry(content="Secret")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    with pytest.raises(ValueError, match="Decryption failed"):
        journal.get_entry(entry_id, passphrase="wrong-passphrase")


def test_no_timestamp_leak_in_filename(temp_data_dir):
    """Test that filenames don't leak timestamp information."""
    entry = JournalEntry(content="Test")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    entries_dir = temp_data_dir / "entries"
    entry_files = list(entries_dir.glob("*.json"))

    assert len(entry_files) == 1
    filename = entry_files[0].name

    # Filename should be: {uuid}.json ONLY
    assert filename == f"{entry_id}.json"

    # Should NOT contain any date/time pattern
    import re

    # Common timestamp patterns
    patterns = [
        r"\d{8}",  # YYYYMMDD
        r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        r"\d{6}",  # HHMMSS
        r"\d{2}:\d{2}:\d{2}",  # HH:MM:SS
    ]

    for pattern in patterns:
        assert not re.search(pattern, filename), f"Timestamp pattern {pattern} found in filename"
