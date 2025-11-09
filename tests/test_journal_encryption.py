"""Tests for journal encryption functionality."""

import tempfile
from pathlib import Path

import pytest

from companion import journal
from companion.models import JournalEntry


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


def test_save_encrypted_entry(temp_data_dir):
    """Test saving an encrypted entry."""
    entry = JournalEntry(content="Secret journal entry")

    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    assert entry_id == entry.id

    # Check file exists with UUID-only name
    entries_dir = temp_data_dir / "entries"
    entry_file = entries_dir / f"{entry_id}.json"
    assert entry_file.exists()

    # Verify file doesn't contain plaintext
    with open(entry_file) as f:
        content = f.read()
        assert "Secret journal entry" not in content
        assert "ciphertext" in content
        assert "salt" in content
        assert "nonce" in content


def test_save_and_retrieve_encrypted(temp_data_dir):
    """Test saving and retrieving encrypted entry."""
    entry = JournalEntry(content="Private thoughts")

    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)
    retrieved = journal.get_entry(entry_id, passphrase=TEST_PASSPHRASE)

    assert retrieved is not None
    assert retrieved.id == entry.id
    assert retrieved.content == "Private thoughts"


def test_retrieve_encrypted_without_passphrase(temp_data_dir):
    """Test that encrypted entry can't be read without passphrase."""
    entry = JournalEntry(content="Secret")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    with pytest.raises(ValueError, match="encrypted but no passphrase"):
        journal.get_entry(entry_id, passphrase=None)


def test_retrieve_encrypted_wrong_passphrase(temp_data_dir):
    """Test that wrong passphrase fails decryption."""
    entry = JournalEntry(content="Secret")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    with pytest.raises(ValueError, match="Decryption failed"):
        journal.get_entry(entry_id, passphrase="wrong-passphrase")


def test_uuid_only_filename(temp_data_dir):
    """Test that filenames only contain UUID (no timestamp)."""
    entry = JournalEntry(content="Test")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    entries_dir = temp_data_dir / "entries"
    entry_files = list(entries_dir.glob("*.json"))

    assert len(entry_files) == 1
    filename = entry_files[0].name

    # Filename should be: {uuid}.json
    assert filename == f"{entry_id}.json"

    # Should NOT contain timestamp pattern (YYYYMMDD_HHMMSS)
    import re

    timestamp_pattern = r"\d{8}_\d{6}"
    assert not re.search(timestamp_pattern, filename)


def test_get_recent_entries_encrypted(temp_data_dir):
    """Test getting recent encrypted entries."""
    entries = [JournalEntry(content=f"Entry {i}") for i in range(3)]

    for entry in entries:
        journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    recent = journal.get_recent_entries(limit=2, passphrase=TEST_PASSPHRASE)

    assert len(recent) == 2
    assert all(isinstance(e, JournalEntry) for e in recent)


def test_get_recent_entries_encrypted_no_passphrase(temp_data_dir):
    """Test that encrypted entries are skipped without passphrase."""
    entries = [JournalEntry(content=f"Entry {i}") for i in range(3)]

    for entry in entries:
        journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    # Should get empty list (entries are encrypted, no passphrase)
    recent = journal.get_recent_entries(limit=5, passphrase=None)

    assert recent == []


def test_search_encrypted_entries(temp_data_dir):
    """Test searching encrypted entries."""
    entry1 = JournalEntry(content="I went to the park")
    entry2 = JournalEntry(content="Work was challenging")

    journal.save_entry(entry1, passphrase=TEST_PASSPHRASE)
    journal.save_entry(entry2, passphrase=TEST_PASSPHRASE)

    results = journal.search_entries("park", passphrase=TEST_PASSPHRASE)

    assert len(results) == 1
    assert "park" in results[0].content.lower()


def test_delete_encrypted_entry(temp_data_dir):
    """Test deleting encrypted entry."""
    entry = JournalEntry(content="To be deleted")
    entry_id = journal.save_entry(entry, passphrase=TEST_PASSPHRASE)

    deleted = journal.delete_entry(entry_id)
    assert deleted is True

    # Verify file is gone
    entries_dir = temp_data_dir / "entries"
    entry_file = entries_dir / f"{entry_id}.json"
    assert not entry_file.exists()


def test_save_requires_passphrase_when_encryption_enabled(temp_data_dir):
    """Test that save requires passphrase when encryption is enabled."""
    entry = JournalEntry(content="Test")

    with pytest.raises(ValueError, match="Encryption is enabled but no passphrase"):
        journal.save_entry(entry, passphrase=None)
