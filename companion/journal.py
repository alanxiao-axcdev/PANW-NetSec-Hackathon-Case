"""Journal entry CRUD operations.

Provides functions for creating, reading, updating, and searching journal entries.
All entries are stored as JSON files with automatic timestamp-based filenames.
"""

import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from companion.config import load_config
from companion.models import JournalEntry
from companion.storage import list_entry_files
from companion.storage import read_json
from companion.storage import write_json

logger = logging.getLogger(__name__)


def save_entry(entry: JournalEntry) -> str:
    """Save journal entry to storage.

    Creates a new JSON file with timestamp-based filename.
    If entry already has an ID, updates existing file.

    Args:
        entry: JournalEntry to save

    Returns:
        Entry ID (UUID)

    Raises:
        OSError: If unable to write file
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = entry.timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp_str}_{entry.id}.json"
    file_path = entries_dir / filename

    entry_dict = entry.model_dump(mode="json")

    try:
        write_json(file_path, entry_dict)
        logger.info("Saved entry: %s", entry.id)
        return entry.id
    except Exception as e:
        logger.error("Failed to save entry %s: %s", entry.id, e)
        raise


def get_entry(entry_id: str) -> JournalEntry | None:
    """Retrieve entry by ID.

    Searches all entry files for matching ID.

    Args:
        entry_id: UUID of entry to retrieve

    Returns:
        JournalEntry if found, None otherwise

    Raises:
        ValueError: If entry data is invalid
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        logger.debug("Entries directory doesn't exist yet")
        return None

    try:
        entry_files = list_entry_files(entries_dir)
    except FileNotFoundError:
        return None

    for file_path in entry_files:
        if entry_id in file_path.name:
            try:
                entry_dict = read_json(file_path)
                return JournalEntry(**entry_dict)
            except Exception as e:
                logger.error("Failed to load entry from %s: %s", file_path, e)
                raise ValueError(f"Invalid entry data in {file_path}") from e

    logger.debug("Entry not found: %s", entry_id)
    return None


def get_recent_entries(limit: int = 10) -> list[JournalEntry]:
    """Get most recent journal entries.

    Returns entries sorted by timestamp (newest first).

    Args:
        limit: Maximum number of entries to return (default: 10)

    Returns:
        List of JournalEntry objects, newest first

    Raises:
        ValueError: If limit is negative
    """
    if limit < 0:
        msg = "Limit must be non-negative"
        raise ValueError(msg)

    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        logger.debug("No entries exist yet")
        return []

    try:
        entry_files = list_entry_files(entries_dir)
    except FileNotFoundError:
        return []

    entry_files.reverse()

    entries: list[JournalEntry] = []
    for file_path in entry_files[:limit]:
        try:
            entry_dict = read_json(file_path)
            entry = JournalEntry(**entry_dict)
            entries.append(entry)
        except Exception as e:
            logger.warning("Failed to load entry from %s: %s", file_path, e)
            continue

    logger.debug("Loaded %d recent entries", len(entries))
    return entries


def get_entries_by_date_range(
    start: date,
    end: date,
) -> list[JournalEntry]:
    """Get entries within date range.

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)

    Returns:
        List of JournalEntry objects in date range

    Raises:
        ValueError: If start date is after end date
    """
    if start > end:
        msg = "Start date must be before or equal to end date"
        raise ValueError(msg)

    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        return []

    try:
        entry_files = list_entry_files(entries_dir)
    except FileNotFoundError:
        return []

    start_datetime = datetime.combine(start, datetime.min.time())
    end_datetime = datetime.combine(end, datetime.max.time())

    entries: list[JournalEntry] = []
    for file_path in entry_files:
        try:
            entry_dict = read_json(file_path)
            entry = JournalEntry(**entry_dict)

            if start_datetime <= entry.timestamp <= end_datetime:
                entries.append(entry)
        except Exception as e:
            logger.warning("Failed to load entry from %s: %s", file_path, e)
            continue

    logger.debug("Found %d entries in date range %s to %s", len(entries), start, end)
    return entries


def search_entries(query: str) -> list[JournalEntry]:
    """Search entries by text content.

    Performs case-insensitive substring search in entry content.

    Args:
        query: Search query string

    Returns:
        List of matching JournalEntry objects

    Raises:
        ValueError: If query is empty
    """
    if not query or not query.strip():
        msg = "Search query cannot be empty"
        raise ValueError(msg)

    query_lower = query.lower()

    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        return []

    try:
        entry_files = list_entry_files(entries_dir)
    except FileNotFoundError:
        return []

    matches: list[JournalEntry] = []
    for file_path in entry_files:
        try:
            entry_dict = read_json(file_path)
            entry = JournalEntry(**entry_dict)

            if query_lower in entry.content.lower():
                matches.append(entry)
        except Exception as e:
            logger.warning("Failed to load entry from %s: %s", file_path, e)
            continue

    logger.debug("Found %d entries matching query: %s", len(matches), query)
    return matches


def delete_entry(entry_id: str) -> bool:
    """Delete entry by ID.

    Args:
        entry_id: UUID of entry to delete

    Returns:
        True if entry was deleted, False if not found

    Raises:
        OSError: If unable to delete file
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        return False

    try:
        entry_files = list_entry_files(entries_dir)
    except FileNotFoundError:
        return False

    for file_path in entry_files:
        if entry_id in file_path.name:
            try:
                file_path.unlink()
                logger.info("Deleted entry: %s", entry_id)
                return True
            except Exception as e:
                logger.error("Failed to delete entry %s: %s", entry_id, e)
                raise

    logger.debug("Entry not found for deletion: %s", entry_id)
    return False
