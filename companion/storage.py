"""JSON file storage operations.

Provides simple file-based storage for journal entries and analysis results.
All data is stored as JSON for human readability and debuggability.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_json(file_path: Path) -> dict[str, Any]:
    """Read JSON file, return dict.

    Args:
        file_path: Path to JSON file to read

    Returns:
        Dictionary parsed from JSON file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file contains invalid JSON
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    try:
        with file_path.open(encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Read JSON from %s", file_path)
        return data
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in {file_path}: {e}"
        raise ValueError(msg) from e


def write_json(file_path: Path, data: dict[str, Any]) -> None:
    """Write dict to JSON file.

    Creates parent directories if they don't exist. Writes with indentation
    for human readability.

    Args:
        file_path: Path where JSON file should be written
        data: Dictionary to serialize to JSON

    Raises:
        OSError: If unable to create directories or write file
        TypeError: If data contains non-serializable objects
    """
    ensure_dir(file_path.parent)

    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.debug("Wrote JSON to %s", file_path)
    except TypeError as e:
        msg = f"Cannot serialize data to JSON: {e}"
        raise TypeError(msg) from e
    except OSError as e:
        logger.error("Failed to write JSON to %s: %s", file_path, e)
        raise


def ensure_dir(directory: Path) -> None:
    """Create directory if doesn't exist.

    Creates all parent directories as needed. Does nothing if directory
    already exists.

    Args:
        directory: Path to directory to create

    Raises:
        OSError: If unable to create directory
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory exists: %s", directory)
    except OSError as e:
        logger.error("Failed to create directory %s: %s", directory, e)
        raise


def list_entry_files(entries_dir: Path) -> list[Path]:
    """List all entry JSON files, sorted by timestamp.

    Finds all .json files in the entries directory and returns them
    sorted by modification time (oldest first).

    Args:
        entries_dir: Directory containing entry JSON files

    Returns:
        List of Path objects for entry files, sorted by modification time

    Raises:
        FileNotFoundError: If entries_dir doesn't exist
    """
    if not entries_dir.exists():
        msg = f"Entries directory not found: {entries_dir}"
        raise FileNotFoundError(msg)

    if not entries_dir.is_dir():
        msg = f"Path is not a directory: {entries_dir}"
        raise NotADirectoryError(msg)

    # Find all .json files
    entry_files = list(entries_dir.glob("*.json"))

    # Sort by modification time (oldest first)
    entry_files.sort(key=lambda p: p.stat().st_mtime)

    logger.debug("Found %d entry files in %s", len(entry_files), entries_dir)
    return entry_files


def backup_file(file_path: Path, backup_suffix: str = ".bak") -> Path:
    """Create backup copy of file.

    Creates a backup by copying the file with a suffix. If a backup already
    exists, it will be overwritten.

    Args:
        file_path: File to backup
        backup_suffix: Suffix to add to backup filename (default: .bak)

    Returns:
        Path to created backup file

    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If unable to create backup
    """
    if not file_path.exists():
        msg = f"Cannot backup non-existent file: {file_path}"
        raise FileNotFoundError(msg)

    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

    try:
        # Read and write to create backup
        content = file_path.read_bytes()
        backup_path.write_bytes(content)
        logger.debug("Created backup: %s", backup_path)
        return backup_path
    except OSError as e:
        logger.error("Failed to create backup of %s: %s", file_path, e)
        raise


def delete_file(file_path: Path, missing_ok: bool = False) -> None:
    """Delete file from filesystem.

    Args:
        file_path: File to delete
        missing_ok: If True, don't raise error if file doesn't exist

    Raises:
        FileNotFoundError: If file doesn't exist and missing_ok is False
        OSError: If unable to delete file
    """
    if not file_path.exists():
        if not missing_ok:
            msg = f"Cannot delete non-existent file: {file_path}"
            raise FileNotFoundError(msg)
        return

    try:
        file_path.unlink()
        logger.debug("Deleted file: %s", file_path)
    except OSError as e:
        logger.error("Failed to delete %s: %s", file_path, e)
        raise
