"""Tests for journal module."""

import tempfile
from datetime import date, datetime, timedelta
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
        config = Config(data_directory=temp_path)

        def mock_load_config():
            return config

        monkeypatch.setattr("companion.journal.load_config", mock_load_config)

        yield temp_path


def test_save_entry(temp_data_dir):
    """Test saving a journal entry."""
    entry = JournalEntry(
        content="Test entry content",
    )

    entry_id = journal.save_entry(entry)

    assert entry_id == entry.id

    entries_dir = temp_data_dir / "entries"
    assert entries_dir.exists()

    entry_files = list(entries_dir.glob("*.json"))
    assert len(entry_files) == 1


def test_save_and_retrieve_entry(temp_data_dir):
    """Test saving and retrieving an entry."""
    entry = JournalEntry(
        content="Test content",
        prompt_used="What's on your mind?",
    )

    entry_id = journal.save_entry(entry)
    retrieved = journal.get_entry(entry_id)

    assert retrieved is not None
    assert retrieved.id == entry.id
    assert retrieved.content == entry.content
    assert retrieved.prompt_used == entry.prompt_used


def test_get_entry_not_found(temp_data_dir):
    """Test retrieving non-existent entry."""
    result = journal.get_entry("nonexistent-id")
    assert result is None


def test_get_recent_entries(temp_data_dir):
    """Test getting recent entries."""
    entries = [
        JournalEntry(content=f"Entry {i}")
        for i in range(5)
    ]

    for entry in entries:
        journal.save_entry(entry)

    recent = journal.get_recent_entries(limit=3)

    assert len(recent) == 3
    assert all(isinstance(e, JournalEntry) for e in recent)


def test_get_recent_entries_empty(temp_data_dir):
    """Test getting recent entries when none exist."""
    recent = journal.get_recent_entries()
    assert recent == []


def test_get_recent_entries_negative_limit(temp_data_dir):
    """Test that negative limit raises error."""
    with pytest.raises(ValueError, match="Limit must be non-negative"):
        journal.get_recent_entries(limit=-1)


def test_get_entries_by_date_range(temp_data_dir):
    """Test getting entries by date range."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    entry1 = JournalEntry(
        content="Two days ago",
        timestamp=datetime.combine(two_days_ago, datetime.min.time()),
    )
    entry2 = JournalEntry(
        content="Yesterday",
        timestamp=datetime.combine(yesterday, datetime.min.time()),
    )
    entry3 = JournalEntry(
        content="Today",
        timestamp=datetime.combine(today, datetime.min.time()),
    )

    journal.save_entry(entry1)
    journal.save_entry(entry2)
    journal.save_entry(entry3)

    entries = journal.get_entries_by_date_range(yesterday, today)

    assert len(entries) == 2
    assert any(e.content == "Yesterday" for e in entries)
    assert any(e.content == "Today" for e in entries)


def test_get_entries_by_date_range_invalid(temp_data_dir):
    """Test that invalid date range raises error."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    with pytest.raises(ValueError, match="Start date must be before or equal"):
        journal.get_entries_by_date_range(today, yesterday)


def test_search_entries(temp_data_dir):
    """Test searching entries by content."""
    entry1 = JournalEntry(content="I went to the park today")
    entry2 = JournalEntry(content="Work was challenging")
    entry3 = JournalEntry(content="Park visit was refreshing")

    journal.save_entry(entry1)
    journal.save_entry(entry2)
    journal.save_entry(entry3)

    results = journal.search_entries("park")

    assert len(results) == 2
    assert all("park" in e.content.lower() for e in results)


def test_search_entries_empty_query(temp_data_dir):
    """Test that empty query raises error."""
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        journal.search_entries("")


def test_search_entries_case_insensitive(temp_data_dir):
    """Test that search is case-insensitive."""
    entry = JournalEntry(content="HELLO World")
    journal.save_entry(entry)

    results = journal.search_entries("hello")
    assert len(results) == 1

    results = journal.search_entries("WORLD")
    assert len(results) == 1


def test_delete_entry(temp_data_dir):
    """Test deleting an entry."""
    entry = JournalEntry(content="To be deleted")
    entry_id = journal.save_entry(entry)

    deleted = journal.delete_entry(entry_id)
    assert deleted is True

    retrieved = journal.get_entry(entry_id)
    assert retrieved is None


def test_delete_entry_not_found(temp_data_dir):
    """Test deleting non-existent entry."""
    deleted = journal.delete_entry("nonexistent-id")
    assert deleted is False
