"""Tests for key rotation functionality.

Comprehensive tests covering:
- Passphrase verification
- Full rotation process
- Backup creation
- Error handling
- Atomic operations
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from companion.models import RotationMetadata, RotationResult
from companion.security.encryption import (
    decrypt_entry,
    decrypt_full_entry_from_dict,
    encrypt_entry,
    encrypt_full_entry_to_dict,
    get_rotation_metadata,
    rotate_keys,
    save_rotation_metadata,
    should_rotate,
    verify_passphrase,
)


@pytest.fixture
def test_entries_dir(tmp_path: Path) -> Path:
    """Create temporary directory with test entries."""
    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()
    return entries_dir


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def create_test_entries(test_entries_dir: Path) -> callable:
    """Factory to create test encrypted entries."""

    def _create(count: int, passphrase: str) -> list[Path]:
        """Create N encrypted test entries.

        Args:
            count: Number of entries to create
            passphrase: Passphrase to encrypt with

        Returns:
            List of created entry file paths
        """
        import json
        from companion.security.encryption import encrypt_full_entry_to_dict

        files = []
        for i in range(count):
            # Create entry dict (what journal actually saves)
            entry_dict = {
                "id": f"test_{i}",
                "content": f"Test journal entry {i}",
                "timestamp": "2025-01-01T00:00:00"
            }
            # Encrypt as dict (JSON format that verify_passphrase expects)
            encrypted_dict = encrypt_full_entry_to_dict(entry_dict, passphrase)
            file_path = test_entries_dir / f"entry_{i}.json"
            file_path.write_text(json.dumps(encrypted_dict))
            files.append(file_path)
        return files

    return _create


class TestPassphraseVerification:
    """Tests for passphrase verification."""

    def test_verify_correct_passphrase(self, test_entries_dir: Path) -> None:
        """Test verification with correct passphrase."""
        # Create test file with full entry format
        entry_dict = {"id": "test", "content": "Secret content"}
        passphrase = "correct_pass"
        encrypted_dict = encrypt_full_entry_to_dict(entry_dict, passphrase)
        test_file = test_entries_dir / "test.json"
        test_file.write_text(json.dumps(encrypted_dict))

        # Verify
        assert verify_passphrase(passphrase, test_file) is True

    def test_verify_wrong_passphrase(self, test_entries_dir: Path) -> None:
        """Test verification with wrong passphrase."""
        # Create test file with full entry format
        entry_dict = {"id": "test", "content": "Secret content"}
        encrypted_dict = encrypt_full_entry_to_dict(entry_dict, "correct_pass")
        test_file = test_entries_dir / "test.json"
        test_file.write_text(json.dumps(encrypted_dict))

        # Verify with wrong passphrase
        assert verify_passphrase("wrong_pass", test_file) is False

    def test_verify_missing_file(self, test_entries_dir: Path) -> None:
        """Test verification with missing file."""
        missing_file = test_entries_dir / "nonexistent.json"
        assert verify_passphrase("any_pass", missing_file) is False

    def test_verify_corrupted_file(self, test_entries_dir: Path) -> None:
        """Test verification with corrupted file."""
        corrupted_file = test_entries_dir / "corrupted.json"
        corrupted_file.write_bytes(b"not valid encrypted data")
        assert verify_passphrase("any_pass", corrupted_file) is False


class TestKeyRotation:
    """Tests for key rotation process."""

    def test_rotate_empty_directory(self, test_entries_dir: Path) -> None:
        """Test rotation with no entries."""
        result = rotate_keys("old", "new", test_entries_dir)

        assert result.success is True
        assert result.entries_rotated == 0
        assert result.entries_failed == 0
        assert "No encrypted entries found" in result.errors

    def test_rotate_single_entry(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotation with single entry."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"

        # Create entry
        files = create_test_entries(1, old_pass)

        # Rotate
        result = rotate_keys(old_pass, new_pass, test_entries_dir)

        # Verify success
        assert result.success is True
        assert result.entries_rotated == 1
        assert result.entries_failed == 0
        assert len(result.errors) == 0

        # Verify old passphrase no longer works
        assert verify_passphrase(old_pass, files[0]) is False

        # Verify new passphrase works
        assert verify_passphrase(new_pass, files[0]) is True

        # Verify content is intact
        with open(files[0]) as f:
            encrypted_dict = json.load(f)
        decrypted_dict = decrypt_full_entry_from_dict(encrypted_dict, new_pass)
        assert decrypted_dict["content"] == "Test journal entry 0"

    def test_rotate_multiple_entries(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotation with multiple entries."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"
        count = 10

        # Create entries
        files = create_test_entries(count, old_pass)

        # Rotate
        result = rotate_keys(old_pass, new_pass, test_entries_dir)

        # Verify success
        assert result.success is True
        assert result.entries_rotated == count
        assert result.entries_failed == 0

        # Verify all entries work with new passphrase
        for i, file_path in enumerate(files):
            assert verify_passphrase(new_pass, file_path) is True
            with open(file_path) as f:
                encrypted_dict = json.load(f)
            decrypted_dict = decrypt_full_entry_from_dict(encrypted_dict, new_pass)
            assert decrypted_dict["content"] == f"Test journal entry {i}"

    def test_rotate_wrong_old_passphrase(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotation with incorrect old passphrase."""
        old_pass = "old_passphrase"
        wrong_pass = "wrong_passphrase"
        new_pass = "new_passphrase"

        # Create entries
        create_test_entries(3, old_pass)

        # Attempt rotation with wrong passphrase
        result = rotate_keys(wrong_pass, new_pass, test_entries_dir)

        # Verify failure
        assert result.success is False
        assert result.entries_rotated == 0
        assert "Old passphrase is incorrect" in result.errors

    def test_rotate_with_backup(
        self, test_entries_dir: Path, tmp_path: Path, create_test_entries: callable
    ) -> None:
        """Test rotation creates backup."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"
        backup_dir = tmp_path / "backup"

        # Create entries
        files = create_test_entries(3, old_pass)

        # Rotate with backup
        result = rotate_keys(old_pass, new_pass, test_entries_dir, backup_dir)

        # Verify success
        assert result.success is True
        assert result.entries_rotated == 3

        # Verify backup exists
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("*.json"))
        assert len(backup_files) == 3

        # Verify backup files still use old passphrase
        for backup_file in backup_files:
            assert verify_passphrase(old_pass, backup_file) is True
            assert verify_passphrase(new_pass, backup_file) is False

    def test_rotate_atomic_operations(
        self, test_entries_dir: Path, create_test_entries: callable, monkeypatch
    ) -> None:
        """Test atomic file operations during rotation."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"

        # Create entries
        files = create_test_entries(3, old_pass)

        # Track if temp files are created and then replaced
        temp_files_seen = []

        original_replace = Path.replace

        def track_replace(self: Path, target: Path) -> Path:
            """Track when temp files are replaced."""
            if self.suffix == ".tmp":
                temp_files_seen.append(self.name)
            return original_replace(self, target)

        monkeypatch.setattr(Path, "replace", track_replace)

        # Rotate
        result = rotate_keys(old_pass, new_pass, test_entries_dir)

        # Verify atomic operations (temp files used)
        assert result.success is True
        assert len(temp_files_seen) == 3

        # Verify no temp files remain
        temp_files = list(test_entries_dir.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_rotate_performance(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotation completes in reasonable time."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"

        # Create 50 entries
        create_test_entries(50, old_pass)

        # Rotate
        result = rotate_keys(old_pass, new_pass, test_entries_dir)

        # Verify reasonable performance (~140ms per entry max)
        # Note: PBKDF2 with 600k iterations is intentionally slow for security
        assert result.success is True
        assert result.entries_rotated == 50
        assert result.duration_seconds < 10.0  # 50 * 200ms = 10s max


class TestRotationMetadata:
    """Tests for rotation metadata management."""

    def test_save_and_load_metadata(self, test_config_dir: Path) -> None:
        """Test saving and loading rotation metadata."""
        now = datetime.now()
        next_due = now + timedelta(days=90)

        metadata = RotationMetadata(
            last_rotation=now,
            rotation_interval_days=90,
            next_rotation_due=next_due,
            total_rotations=5,
        )

        # Save
        save_rotation_metadata(metadata, test_config_dir)

        # Load
        loaded = get_rotation_metadata(test_config_dir)

        # Verify
        assert loaded is not None
        assert loaded.rotation_interval_days == 90
        assert loaded.total_rotations == 5

    def test_load_missing_metadata(self, test_config_dir: Path) -> None:
        """Test loading when metadata file doesn't exist."""
        metadata = get_rotation_metadata(test_config_dir)
        assert metadata is None

    def test_load_corrupted_metadata(self, test_config_dir: Path) -> None:
        """Test loading corrupted metadata file."""
        # Write invalid JSON
        metadata_file = test_config_dir / "rotation_metadata.json"
        metadata_file.write_text("not valid json {")

        # Should return None on error
        metadata = get_rotation_metadata(test_config_dir)
        assert metadata is None

    def test_should_rotate_no_metadata(self, test_config_dir: Path) -> None:
        """Test should_rotate with no previous rotation."""
        assert should_rotate(test_config_dir) is False

    def test_should_rotate_not_due(self, test_config_dir: Path) -> None:
        """Test should_rotate when not yet due."""
        now = datetime.now()
        next_due = now + timedelta(days=30)  # 30 days in future

        metadata = RotationMetadata(
            last_rotation=now - timedelta(days=60),
            rotation_interval_days=90,
            next_rotation_due=next_due,
            total_rotations=1,
        )
        save_rotation_metadata(metadata, test_config_dir)

        assert should_rotate(test_config_dir) is False

    def test_should_rotate_due(self, test_config_dir: Path) -> None:
        """Test should_rotate when rotation is due."""
        now = datetime.now()
        past_due = now - timedelta(days=1)  # 1 day ago

        metadata = RotationMetadata(
            last_rotation=now - timedelta(days=91),
            rotation_interval_days=90,
            next_rotation_due=past_due,
            total_rotations=1,
        )
        save_rotation_metadata(metadata, test_config_dir)

        assert should_rotate(test_config_dir) is True

    def test_should_rotate_custom_interval(self, test_config_dir: Path) -> None:
        """Test should_rotate with custom interval."""
        now = datetime.now()
        next_due = now + timedelta(days=20)  # 20 days in future

        metadata = RotationMetadata(
            last_rotation=now - timedelta(days=40),
            rotation_interval_days=60,
            next_rotation_due=next_due,
            total_rotations=1,
        )
        save_rotation_metadata(metadata, test_config_dir)

        # Not due yet (60 day interval, only 40 days passed)
        assert should_rotate(test_config_dir, rotation_interval_days=60) is False


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_rotate_with_partial_corruption(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotation handles corrupted entries gracefully."""
        old_pass = "old_passphrase"
        new_pass = "new_passphrase"

        # Create good entries
        create_test_entries(3, old_pass)

        # Create corrupted entry
        corrupted = test_entries_dir / "corrupted.json"
        corrupted.write_bytes(b"not valid encrypted data")

        # Rotate
        result = rotate_keys(old_pass, new_pass, test_entries_dir)

        # Should succeed for good entries, fail for corrupted
        assert result.success is False  # Overall failure due to one corrupted
        assert result.entries_rotated == 3
        assert result.entries_failed == 1
        assert len(result.errors) == 1
        assert "corrupted.json" in result.errors[0]

    def test_rotate_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test rotation with nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"

        result = rotate_keys("old", "new", nonexistent)

        # Should handle gracefully
        assert result.success is True
        assert result.entries_rotated == 0

    def test_rotation_result_model(self) -> None:
        """Test RotationResult model validation."""
        # Valid result
        result = RotationResult(
            success=True,
            entries_rotated=10,
            entries_failed=2,
            errors=["error1", "error2"],
            duration_seconds=3.5,
        )

        assert result.success is True
        assert result.entries_rotated == 10
        assert result.entries_failed == 2
        assert len(result.errors) == 2

        # Minimal result (defaults)
        minimal = RotationResult(success=True, entries_rotated=5)
        assert minimal.entries_failed == 0
        assert minimal.errors == []
        assert minimal.duration_seconds == 0.0

    def test_rotation_metadata_model(self) -> None:
        """Test RotationMetadata model validation."""
        now = datetime.now()
        next_due = now + timedelta(days=90)

        metadata = RotationMetadata(
            last_rotation=now,
            rotation_interval_days=90,
            next_rotation_due=next_due,
            total_rotations=3,
        )

        assert metadata.rotation_interval_days == 90
        assert metadata.total_rotations == 3

        # Test default interval
        metadata_default = RotationMetadata(
            last_rotation=now, next_rotation_due=next_due, total_rotations=0
        )
        assert metadata_default.rotation_interval_days == 90
        assert metadata_default.total_rotations == 0


class TestIntegration:
    """Integration tests for full rotation workflow."""

    def test_full_rotation_workflow(
        self, test_entries_dir: Path, test_config_dir: Path, create_test_entries: callable, tmp_path: Path
    ) -> None:
        """Test complete rotation workflow end-to-end."""
        old_pass = "old_passphrase_123"
        new_pass = "new_passphrase_456"
        backup_dir = tmp_path / "backup"

        # Step 1: Create entries
        files = create_test_entries(5, old_pass)

        # Step 2: Verify initial state
        for file_path in files:
            assert verify_passphrase(old_pass, file_path) is True

        # Step 3: Rotate keys with backup
        result = rotate_keys(old_pass, new_pass, test_entries_dir, backup_dir)

        # Step 4: Verify rotation success
        assert result.success is True
        assert result.entries_rotated == 5
        assert result.entries_failed == 0

        # Step 5: Verify backup created
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("*.json"))
        assert len(backup_files) == 5

        # Step 6: Verify old passphrase no longer works on originals
        for file_path in files:
            assert verify_passphrase(old_pass, file_path) is False
            assert verify_passphrase(new_pass, file_path) is True

        # Step 7: Verify backup still uses old passphrase
        for backup_file in backup_files:
            assert verify_passphrase(old_pass, backup_file) is True

        # Step 8: Save metadata
        now = datetime.now()
        metadata = RotationMetadata(
            last_rotation=now,
            rotation_interval_days=90,
            next_rotation_due=now + timedelta(days=90),
            total_rotations=1,
        )
        save_rotation_metadata(metadata, test_config_dir)

        # Step 9: Verify metadata persisted
        loaded = get_rotation_metadata(test_config_dir)
        assert loaded is not None
        assert loaded.total_rotations == 1

        # Step 10: Verify content integrity
        for i, file_path in enumerate(files):
            with open(file_path) as f:
                encrypted_dict = json.load(f)
            decrypted_dict = decrypt_full_entry_from_dict(encrypted_dict, new_pass)
            assert decrypted_dict["content"] == f"Test journal entry {i}"

    def test_rotation_then_second_rotation(
        self, test_entries_dir: Path, create_test_entries: callable
    ) -> None:
        """Test rotating keys twice in succession."""
        pass1 = "passphrase_1"
        pass2 = "passphrase_2"
        pass3 = "passphrase_3"

        # Create entries
        files = create_test_entries(3, pass1)

        # First rotation
        result1 = rotate_keys(pass1, pass2, test_entries_dir)
        assert result1.success is True
        assert result1.entries_rotated == 3

        # Verify first rotation
        for file_path in files:
            assert verify_passphrase(pass2, file_path) is True

        # Second rotation
        result2 = rotate_keys(pass2, pass3, test_entries_dir)
        assert result2.success is True
        assert result2.entries_rotated == 3

        # Verify second rotation
        for file_path in files:
            assert verify_passphrase(pass3, file_path) is True
            assert verify_passphrase(pass2, file_path) is False
            assert verify_passphrase(pass1, file_path) is False

        # Verify content still intact
        for i, file_path in enumerate(files):
            with open(file_path) as f:
                encrypted_dict = json.load(f)
            decrypted_dict = decrypt_full_entry_from_dict(encrypted_dict, pass3)
            assert decrypted_dict["content"] == f"Test journal entry {i}"
