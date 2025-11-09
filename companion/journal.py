"""Journal entry CRUD operations.

Provides functions for creating, reading, updating, and searching journal entries.
All entries are stored as JSON files with UUID-only filenames for privacy.
ALL entry data (content + metadata) is encrypted using AES-256-GCM when encryption is enabled.
"""

import logging
from datetime import date, datetime

from companion.config import load_config
from companion.models import JournalEntry
from companion.security.encryption import (
    decrypt_entry_from_dict,
    decrypt_full_entry_from_dict,
    encrypt_full_entry_to_dict,
)
from companion.storage import ensure_dir, list_entry_files, read_json, write_json

logger = logging.getLogger(__name__)


def _is_encrypted(entry_data: dict) -> bool:
    """Check if entry data is encrypted.

    Args:
        entry_data: Dictionary containing entry data

    Returns:
        True if data appears to be encrypted (has salt/nonce/ciphertext)
    """
    return all(key in entry_data for key in ["salt", "nonce", "ciphertext"])


def _is_legacy_encryption(entry_data: dict) -> bool:
    """Check if entry uses legacy content-only encryption.

    Legacy format has plaintext metadata fields (timestamp, sentiment, themes, etc.)
    alongside encrypted content.

    Args:
        entry_data: Dictionary containing entry data

    Returns:
        True if this is legacy content-only encryption
    """
    # Legacy has encrypted content BUT also has plaintext metadata
    has_encryption = _is_encrypted(entry_data)
    has_plaintext_metadata = "timestamp" in entry_data or "themes" in entry_data
    return has_encryption and has_plaintext_metadata


def save_entry(entry: JournalEntry, passphrase: str | None = None) -> str:
    """Save journal entry to storage.

    Creates a new JSON file with UUID-only filename for privacy.
    Encrypts ALL entry data (content + metadata) if passphrase provided and encryption enabled.

    Args:
        entry: JournalEntry to save
        passphrase: Optional passphrase for encryption

    Returns:
        Entry ID (UUID)

    Raises:
        OSError: If unable to write file
        ValueError: If encryption enabled but no passphrase provided
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"
    ensure_dir(entries_dir)

    # UUID-only filename for privacy (no timestamp leak)
    filename = f"{entry.id}.json"
    file_path = entries_dir / filename

    # Check if encryption is enabled
    encrypt_enabled = config.enable_encryption

    if encrypt_enabled and not passphrase:
        msg = "Encryption is enabled but no passphrase provided"
        raise ValueError(msg)

    try:
        if encrypt_enabled and passphrase:
            # Get full entry dict
            entry_dict = entry.model_dump(mode="json")

            # Encrypt ENTIRE entry (all metadata + content)
            encrypted_entry = encrypt_full_entry_to_dict(entry_dict, passphrase)

            write_json(file_path, encrypted_entry)
        else:
            # Store plaintext entry
            entry_dict = entry.model_dump(mode="json")
            entry_dict["encrypted"] = False
            write_json(file_path, entry_dict)

        logger.info("Saved entry: %s (encrypted: %s)", entry.id, encrypt_enabled)
        return entry.id

    except Exception as e:
        logger.error("Failed to save entry %s: %s", entry.id, e)
        raise


def get_entry(entry_id: str, passphrase: str | None = None) -> JournalEntry | None:
    """Retrieve entry by ID.

    Searches for entry file by UUID and decrypts if necessary.
    Supports both new full-encryption and legacy content-only encryption.

    Args:
        entry_id: UUID of entry to retrieve
        passphrase: Optional passphrase for decryption

    Returns:
        JournalEntry if found, None otherwise

    Raises:
        ValueError: If entry is encrypted but no passphrase provided or wrong passphrase
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"

    if not entries_dir.exists():
        logger.debug("Entries directory doesn't exist yet")
        return None

    # Look for UUID.json file
    file_path = entries_dir / f"{entry_id}.json"

    if not file_path.exists():
        logger.debug("Entry not found: %s", entry_id)
        return None

    try:
        entry_data = read_json(file_path)

        # Check if encrypted
        if _is_encrypted(entry_data):
            if not passphrase:
                msg = f"Entry {entry_id} is encrypted but no passphrase provided"
                raise ValueError(msg)

            # Check if legacy (content-only) or new (full) encryption
            if _is_legacy_encryption(entry_data):
                # LEGACY: Only content is encrypted, metadata is plaintext
                logger.debug("Decrypting legacy content-only entry: %s", entry_id)
                content = decrypt_entry_from_dict(entry_data, passphrase)
                entry_data["content"] = content
                # Remove encryption fields
                entry_data.pop("salt", None)
                entry_data.pop("nonce", None)
                entry_data.pop("ciphertext", None)
                entry_data.pop("encrypted", None)
            else:
                # NEW: Full entry encryption (all metadata + content)
                logger.debug("Decrypting full entry: %s", entry_id)
                entry_data = decrypt_full_entry_from_dict(entry_data, passphrase)

        return JournalEntry(**entry_data)

    except Exception as e:
        logger.error("Failed to load entry from %s: %s", file_path, e)
        msg = f"Invalid entry data in {file_path}: {e}"
        raise ValueError(msg) from e


def get_recent_entries(limit: int = 10, passphrase: str | None = None) -> list[JournalEntry]:
    """Get most recent journal entries.

    Returns entries sorted by timestamp (newest first).
    Supports both new full-encryption and legacy content-only encryption.

    Args:
        limit: Maximum number of entries to return (default: 10)
        passphrase: Optional passphrase for decrypting entries

    Returns:
        List of JournalEntry objects, newest first

    Raises:
        ValueError: If limit is negative or encrypted entries found without passphrase
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

    # Reverse to get newest first
    entry_files.reverse()

    entries: list[JournalEntry] = []
    for file_path in entry_files[:limit]:
        try:
            entry_data = read_json(file_path)

            # Check if encrypted
            if _is_encrypted(entry_data):
                if not passphrase:
                    logger.warning("Skipping encrypted entry (no passphrase): %s", file_path.name)
                    continue

                # Check if legacy or new encryption
                if _is_legacy_encryption(entry_data):
                    # LEGACY: Content-only encryption
                    content = decrypt_entry_from_dict(entry_data, passphrase)
                    entry_data["content"] = content
                    entry_data.pop("salt", None)
                    entry_data.pop("nonce", None)
                    entry_data.pop("ciphertext", None)
                    entry_data.pop("encrypted", None)
                else:
                    # NEW: Full entry encryption
                    entry_data = decrypt_full_entry_from_dict(entry_data, passphrase)

            entry = JournalEntry(**entry_data)
            entries.append(entry)

        except Exception as e:
            logger.warning("Failed to load entry from %s: %s", file_path, e)
            continue

    logger.debug("Loaded %d recent entries", len(entries))
    return entries


def get_entries_by_date_range(
    start: date,
    end: date,
    passphrase: str | None = None,
) -> list[JournalEntry]:
    """Get entries within date range.

    Supports both new full-encryption and legacy content-only encryption.

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        passphrase: Optional passphrase for decrypting entries

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
            entry_data = read_json(file_path)

            # Check if encrypted
            if _is_encrypted(entry_data):
                if not passphrase:
                    logger.warning("Skipping encrypted entry (no passphrase): %s", file_path.name)
                    continue

                # Check if legacy or new encryption
                if _is_legacy_encryption(entry_data):
                    # LEGACY: Content-only encryption
                    content = decrypt_entry_from_dict(entry_data, passphrase)
                    entry_data["content"] = content
                    entry_data.pop("salt", None)
                    entry_data.pop("nonce", None)
                    entry_data.pop("ciphertext", None)
                    entry_data.pop("encrypted", None)
                else:
                    # NEW: Full entry encryption
                    entry_data = decrypt_full_entry_from_dict(entry_data, passphrase)

            entry = JournalEntry(**entry_data)

            if start_datetime <= entry.timestamp <= end_datetime:
                entries.append(entry)

        except Exception as e:
            logger.warning("Failed to load entry from %s: %s", file_path, e)
            continue

    logger.debug("Found %d entries in date range %s to %s", len(entries), start, end)
    return entries


def search_entries(query: str, passphrase: str | None = None) -> list[JournalEntry]:
    """Search entries by text content.

    Performs case-insensitive substring search in entry content.
    Supports both new full-encryption and legacy content-only encryption.

    Args:
        query: Search query string
        passphrase: Optional passphrase for decrypting entries

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
            entry_data = read_json(file_path)

            # Check if encrypted
            if _is_encrypted(entry_data):
                if not passphrase:
                    logger.warning("Skipping encrypted entry (no passphrase): %s", file_path.name)
                    continue

                # Check if legacy or new encryption
                if _is_legacy_encryption(entry_data):
                    # LEGACY: Content-only encryption
                    content = decrypt_entry_from_dict(entry_data, passphrase)
                    entry_data["content"] = content
                    entry_data.pop("salt", None)
                    entry_data.pop("nonce", None)
                    entry_data.pop("ciphertext", None)
                    entry_data.pop("encrypted", None)
                else:
                    # NEW: Full entry encryption
                    entry_data = decrypt_full_entry_from_dict(entry_data, passphrase)

            entry = JournalEntry(**entry_data)

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

    # UUID-only filename
    file_path = entries_dir / f"{entry_id}.json"

    if not file_path.exists():
        logger.debug("Entry not found for deletion: %s", entry_id)
        return False

    try:
        file_path.unlink()
        logger.info("Deleted entry: %s", entry_id)
        return True
    except Exception as e:
        logger.error("Failed to delete entry %s: %s", entry_id, e)
        raise
