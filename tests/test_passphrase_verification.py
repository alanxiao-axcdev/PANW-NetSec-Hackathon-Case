"""Tests for passphrase verification system."""

import pytest
from pathlib import Path
from companion.security.passphrase import (
    generate_passphrase_hash,
    verify_passphrase_hash,
)
from companion.models import Config


def test_generate_passphrase_hash():
    """Test hash generation."""
    passphrase = "my-secure-journal-2025!"
    hash_str = generate_passphrase_hash(passphrase)

    # Should return base64 string
    assert isinstance(hash_str, str)
    assert len(hash_str) > 0

    # Should be base64-encoded 48 bytes (salt + hash)
    import base64
    decoded = base64.b64decode(hash_str)
    assert len(decoded) == 48  # 16 bytes salt + 32 bytes hash


def test_verify_passphrase_hash_correct():
    """Test verification with correct passphrase."""
    passphrase = "correct-passphrase-123!"
    hash_str = generate_passphrase_hash(passphrase)

    # Should verify successfully
    assert verify_passphrase_hash(passphrase, hash_str) is True


def test_verify_passphrase_hash_incorrect():
    """Test verification with wrong passphrase."""
    correct_passphrase = "correct-passphrase-123!"
    wrong_passphrase = "wrong-passphrase-456!"

    hash_str = generate_passphrase_hash(correct_passphrase)

    # Should fail verification
    assert verify_passphrase_hash(wrong_passphrase, hash_str) is False


def test_verify_passphrase_hash_empty():
    """Test verification with empty inputs."""
    hash_str = generate_passphrase_hash("test")

    # Empty passphrase should fail
    assert verify_passphrase_hash("", hash_str) is False

    # Empty hash should fail
    assert verify_passphrase_hash("test", "") is False


def test_verify_passphrase_hash_invalid_format():
    """Test verification with malformed hash."""
    # Invalid base64
    assert verify_passphrase_hash("test", "not-valid-base64!@#$") is False

    # Valid base64 but wrong length
    import base64
    short_hash = base64.b64encode(b"tooshort").decode()
    assert verify_passphrase_hash("test", short_hash) is False


def test_hash_is_salted():
    """Test that hashes are salted (same passphrase produces different hashes)."""
    passphrase = "my-passphrase"

    hash1 = generate_passphrase_hash(passphrase)
    hash2 = generate_passphrase_hash(passphrase)

    # Different hashes (due to random salt)
    assert hash1 != hash2

    # But both verify the same passphrase
    assert verify_passphrase_hash(passphrase, hash1) is True
    assert verify_passphrase_hash(passphrase, hash2) is True


def test_config_stores_hash(tmp_path: Path):
    """Test that passphrase hash is stored in config."""
    # Create temporary config
    config_file = tmp_path / "config.json"

    cfg = Config(data_directory=tmp_path)
    passphrase_hash = generate_passphrase_hash("test-passphrase")
    cfg.passphrase_hash = passphrase_hash

    # Save and reload
    import json
    with open(config_file, 'w') as f:
        json.dump(cfg.model_dump(mode='json'), f, default=str)

    # Load and verify
    with open(config_file, 'r') as f:
        loaded_data = json.load(f)

    assert 'passphrase_hash' in loaded_data
    assert loaded_data['passphrase_hash'] == passphrase_hash


def test_hash_survives_config_roundtrip(tmp_path: Path):
    """Test that hash persists through config save/load cycle."""
    passphrase = "persistent-passphrase-123"
    hash_str = generate_passphrase_hash(passphrase)

    # Create and save config with hash
    cfg = Config(data_directory=tmp_path, passphrase_hash=hash_str)

    config_file = tmp_path / "config.json"
    import json
    with open(config_file, 'w') as f:
        json.dump(cfg.model_dump(mode='json'), f, default=str)

    # Load config
    with open(config_file, 'r') as f:
        loaded_data = json.load(f)

    loaded_cfg = Config(**loaded_data)

    # Verify hash is intact and works
    assert loaded_cfg.passphrase_hash == hash_str
    assert verify_passphrase_hash(passphrase, loaded_cfg.passphrase_hash) is True


def test_timing_attack_resistance():
    """Test that verification uses constant-time comparison."""
    # This is a basic test - the actual protection is in hmac.compare_digest
    passphrase = "timing-test-passphrase"
    hash_str = generate_passphrase_hash(passphrase)

    # Both correct and incorrect passphrases should take similar time
    # (We can't easily measure this in a unit test, but we verify the code path)

    import time

    # Correct passphrase
    start = time.perf_counter()
    result1 = verify_passphrase_hash(passphrase, hash_str)
    time1 = time.perf_counter() - start
    assert result1 is True

    # Incorrect passphrase (same length)
    start = time.perf_counter()
    result2 = verify_passphrase_hash("timing-test-WRONG-word", hash_str)
    time2 = time.perf_counter() - start
    assert result2 is False

    # Times should be similar (within 100ms)
    # Note: This is a weak test but validates the code path
    assert abs(time1 - time2) < 0.1


def test_empty_passphrase_rejected():
    """Test that empty passphrase cannot be hashed."""
    with pytest.raises(ValueError, match="Passphrase cannot be empty"):
        generate_passphrase_hash("")


def test_hash_uses_pbkdf2():
    """Test that hash uses PBKDF2 with correct parameters."""
    # This test validates the algorithm by checking consistency
    passphrase = "test-pbkdf2"
    hash1 = generate_passphrase_hash(passphrase)

    # Hash should be reproducible with same passphrase and salt
    import base64
    decoded = base64.b64decode(hash1)
    salt = decoded[:16]

    # Manually derive hash with same salt
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
        backend=default_backend(),
    )

    expected_hash = kdf.derive(passphrase.encode("utf-8"))
    actual_hash = decoded[16:]

    assert expected_hash == actual_hash

