"""Tests for JSON file storage operations."""

import json
import time
from datetime import UTC, datetime

import pytest

from companion.storage import (
    backup_file,
    delete_file,
    ensure_dir,
    list_entry_files,
    read_json,
    write_json,
)


def test_read_json_success(tmp_path):
    """Test read_json successfully reads JSON file."""
    test_file = tmp_path / "test.json"
    test_data = {"key": "value", "number": 42}

    with test_file.open("w") as f:
        json.dump(test_data, f)

    result = read_json(test_file)

    assert result == test_data


def test_read_json_file_not_found(tmp_path):
    """Test read_json raises FileNotFoundError for missing file."""
    nonexistent = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="File not found"):
        read_json(nonexistent)


def test_read_json_invalid_json(tmp_path):
    """Test read_json raises ValueError for invalid JSON."""
    test_file = tmp_path / "invalid.json"
    test_file.write_text("{ not valid json }")

    with pytest.raises(ValueError, match="Invalid JSON"):
        read_json(test_file)


def test_write_json_success(tmp_path):
    """Test write_json successfully writes JSON file."""
    test_file = tmp_path / "output.json"
    test_data = {"name": "test", "values": [1, 2, 3]}

    write_json(test_file, test_data)

    assert test_file.exists()

    with test_file.open() as f:
        loaded = json.load(f)

    assert loaded == test_data


def test_write_json_creates_parent_dirs(tmp_path):
    """Test write_json creates parent directories."""
    nested_file = tmp_path / "deep" / "nested" / "file.json"
    test_data = {"created": True}

    write_json(nested_file, test_data)

    assert nested_file.exists()
    assert nested_file.parent.exists()


def test_write_json_overwrites_existing(tmp_path):
    """Test write_json overwrites existing file."""
    test_file = tmp_path / "overwrite.json"

    # Write initial data
    write_json(test_file, {"version": 1})

    # Overwrite
    write_json(test_file, {"version": 2})

    result = read_json(test_file)
    assert result == {"version": 2}


def test_write_json_handles_datetime(tmp_path):
    """Test write_json handles datetime objects via default=str."""
    test_file = tmp_path / "datetime.json"
    now = datetime.now(UTC)
    test_data = {"timestamp": now}

    write_json(test_file, test_data)

    result = read_json(test_file)
    assert isinstance(result["timestamp"], str)


def test_read_write_json_roundtrip(tmp_path):
    """Test data survives write and read roundtrip."""
    test_file = tmp_path / "roundtrip.json"
    test_data = {
        "string": "hello",
        "number": 123,
        "float": 45.67,
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "nested": {"a": 1, "b": 2},
    }

    write_json(test_file, test_data)
    result = read_json(test_file)

    assert result == test_data


def test_ensure_dir_creates_directory(tmp_path):
    """Test ensure_dir creates directory."""
    new_dir = tmp_path / "new_directory"

    assert not new_dir.exists()

    ensure_dir(new_dir)

    assert new_dir.exists()
    assert new_dir.is_dir()


def test_ensure_dir_creates_nested_directories(tmp_path):
    """Test ensure_dir creates nested directory structure."""
    nested_dir = tmp_path / "level1" / "level2" / "level3"

    ensure_dir(nested_dir)

    assert nested_dir.exists()
    assert nested_dir.is_dir()


def test_ensure_dir_idempotent(tmp_path):
    """Test ensure_dir can be called multiple times safely."""
    test_dir = tmp_path / "existing"

    ensure_dir(test_dir)
    ensure_dir(test_dir)  # Call again

    assert test_dir.exists()


def test_list_entry_files_empty_directory(tmp_path):
    """Test list_entry_files returns empty list for empty directory."""
    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()

    result = list_entry_files(entries_dir)

    assert result == []


def test_list_entry_files_finds_json_files(tmp_path):
    """Test list_entry_files finds all JSON files."""
    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()

    # Create some JSON files
    (entries_dir / "entry1.json").write_text("{}")
    (entries_dir / "entry2.json").write_text("{}")
    (entries_dir / "entry3.json").write_text("{}")

    # Create non-JSON file (should be ignored)
    (entries_dir / "readme.txt").write_text("text")

    result = list_entry_files(entries_dir)

    assert len(result) == 3
    assert all(p.suffix == ".json" for p in result)


def test_list_entry_files_sorted_by_time(tmp_path):
    """Test list_entry_files returns files sorted by modification time."""
    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()

    # Create files with small delays to ensure different mtimes
    file1 = entries_dir / "first.json"
    file1.write_text("{}")
    time.sleep(0.01)

    file2 = entries_dir / "second.json"
    file2.write_text("{}")
    time.sleep(0.01)

    file3 = entries_dir / "third.json"
    file3.write_text("{}")

    result = list_entry_files(entries_dir)

    # Should be sorted oldest to newest
    assert result[0].name == "first.json"
    assert result[1].name == "second.json"
    assert result[2].name == "third.json"


def test_list_entry_files_directory_not_found(tmp_path):
    """Test list_entry_files raises FileNotFoundError for missing directory."""
    nonexistent = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="not found"):
        list_entry_files(nonexistent)


def test_list_entry_files_not_a_directory(tmp_path):
    """Test list_entry_files raises NotADirectoryError for file path."""
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("content")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        list_entry_files(not_a_dir)


def test_backup_file_success(tmp_path):
    """Test backup_file creates backup copy."""
    original = tmp_path / "original.json"
    original.write_text('{"data": "original"}')

    backup_path = backup_file(original)

    assert backup_path.exists()
    assert backup_path.name == "original.json.bak"
    assert backup_path.read_text() == '{"data": "original"}'


def test_backup_file_custom_suffix(tmp_path):
    """Test backup_file with custom suffix."""
    original = tmp_path / "file.txt"
    original.write_text("content")

    backup_path = backup_file(original, backup_suffix=".backup")

    assert backup_path.name == "file.txt.backup"


def test_backup_file_overwrites_existing_backup(tmp_path):
    """Test backup_file overwrites existing backup."""
    original = tmp_path / "file.txt"
    original.write_text("new content")

    backup_path = original.with_suffix(original.suffix + ".bak")
    backup_path.write_text("old backup")

    backup_file(original)

    assert backup_path.read_text() == "new content"


def test_backup_file_not_found(tmp_path):
    """Test backup_file raises FileNotFoundError for missing file."""
    nonexistent = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="Cannot backup"):
        backup_file(nonexistent)


def test_delete_file_success(tmp_path):
    """Test delete_file removes file."""
    test_file = tmp_path / "delete_me.json"
    test_file.write_text("{}")

    assert test_file.exists()

    delete_file(test_file)

    assert not test_file.exists()


def test_delete_file_missing_raises_error(tmp_path):
    """Test delete_file raises FileNotFoundError for missing file."""
    nonexistent = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="Cannot delete"):
        delete_file(nonexistent)


def test_delete_file_missing_ok(tmp_path):
    """Test delete_file with missing_ok=True doesn't raise error."""
    nonexistent = tmp_path / "missing.json"

    # Should not raise error
    delete_file(nonexistent, missing_ok=True)
