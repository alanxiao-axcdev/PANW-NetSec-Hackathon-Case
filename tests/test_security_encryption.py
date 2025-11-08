"""Tests for encryption module."""

import base64

import pytest

from companion.security.encryption import (
    decrypt_entry,
    decrypt_entry_from_dict,
    derive_key,
    encrypt_entry,
    encrypt_entry_to_dict,
)


class TestKeyDerivation:
    """Test PBKDF2 key derivation."""

    def test_derive_key_length(self):
        """Derived key should be 32 bytes."""
        salt = b"0" * 16
        key = derive_key("password", salt)
        assert len(key) == 32

    def test_derive_key_deterministic(self):
        """Same passphrase and salt should produce same key."""
        salt = b"0" * 16
        key1 = derive_key("password", salt)
        key2 = derive_key("password", salt)
        assert key1 == key2

    def test_derive_key_different_salts(self):
        """Different salts should produce different keys."""
        key1 = derive_key("password", b"a" * 16)
        key2 = derive_key("password", b"b" * 16)
        assert key1 != key2

    def test_derive_key_empty_passphrase(self):
        """Should raise ValueError for empty passphrase."""
        with pytest.raises(ValueError, match="Passphrase cannot be empty"):
            derive_key("", b"0" * 16)

    def test_derive_key_short_salt(self):
        """Should raise ValueError for short salt."""
        with pytest.raises(ValueError, match="Salt must be at least"):
            derive_key("password", b"short")


class TestEncryption:
    """Test AES-256-GCM encryption."""

    def test_encrypt_basic(self):
        """Should encrypt content successfully."""
        encrypted = encrypt_entry("Hello, World!", "password")
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_encrypt_empty_content(self):
        """Should raise ValueError for empty content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            encrypt_entry("", "password")

    def test_encrypt_empty_passphrase(self):
        """Should raise ValueError for empty passphrase."""
        with pytest.raises(ValueError, match="Passphrase cannot be empty"):
            encrypt_entry("content", "")

    def test_encrypt_unicode(self):
        """Should handle Unicode content."""
        content = "Hello 世界 🌍"
        encrypted = encrypt_entry(content, "password")
        assert len(encrypted) > 0

    def test_encrypt_long_content(self):
        """Should handle long content."""
        content = "x" * 10000
        encrypted = encrypt_entry(content, "password")
        assert len(encrypted) > len(content)


class TestDecryption:
    """Test AES-256-GCM decryption."""

    def test_decrypt_basic(self):
        """Should decrypt encrypted content."""
        content = "Secret message"
        passphrase = "secure_password"

        encrypted = encrypt_entry(content, passphrase)
        decrypted = decrypt_entry(encrypted, passphrase)

        assert decrypted == content

    def test_decrypt_wrong_passphrase(self):
        """Should raise ValueError for wrong passphrase."""
        encrypted = encrypt_entry("content", "right")

        with pytest.raises(ValueError, match="wrong passphrase or tampered"):
            decrypt_entry(encrypted, "wrong")

    def test_decrypt_empty_data(self):
        """Should raise ValueError for empty encrypted data."""
        with pytest.raises(ValueError, match="Encrypted data cannot be empty"):
            decrypt_entry(b"", "password")

    def test_decrypt_short_data(self):
        """Should raise ValueError for too short data."""
        with pytest.raises(ValueError, match="Encrypted data too short"):
            decrypt_entry(b"short", "password")

    def test_decrypt_corrupted_data(self):
        """Should raise ValueError for corrupted data."""
        encrypted = encrypt_entry("content", "password")
        corrupted = encrypted[:-10] + b"corrupted!"

        with pytest.raises(ValueError, match="wrong passphrase or tampered"):
            decrypt_entry(corrupted, "password")

    def test_decrypt_unicode(self):
        """Should handle Unicode content."""
        content = "Hello 世界 🌍"
        encrypted = encrypt_entry(content, "password")
        decrypted = decrypt_entry(encrypted, "password")
        assert decrypted == content


class TestEncryptionRoundTrip:
    """Test encryption/decryption round trips."""

    @pytest.mark.parametrize(
        "content",
        [
            "Short",
            "Medium length content with spaces",
            "x" * 1000,
            "Unicode: 日本語 العربية",
            "Special chars: !@#$%^&*()",
        ],
    )
    def test_roundtrip_various_content(self, content):
        """Should correctly encrypt and decrypt various content."""
        passphrase = "test_password"
        encrypted = encrypt_entry(content, passphrase)
        decrypted = decrypt_entry(encrypted, passphrase)
        assert decrypted == content

    def test_roundtrip_different_passphrases(self):
        """Different passphrases should produce different ciphertexts."""
        content = "Same content"
        enc1 = encrypt_entry(content, "pass1")
        enc2 = encrypt_entry(content, "pass2")
        assert enc1 != enc2

    def test_roundtrip_same_content_different_ciphertext(self):
        """Same content should produce different ciphertext due to random nonce."""
        content = "Same content"
        passphrase = "password"
        enc1 = encrypt_entry(content, passphrase)
        enc2 = encrypt_entry(content, passphrase)
        assert enc1 != enc2  # Different due to random nonce


class TestDictFormat:
    """Test dictionary format for JSON storage."""

    def test_encrypt_to_dict(self):
        """Should produce dict with required keys."""
        result = encrypt_entry_to_dict("content", "password")

        assert isinstance(result, dict)
        assert "salt" in result
        assert "nonce" in result
        assert "ciphertext" in result

        # All should be base64-encoded strings
        assert isinstance(result["salt"], str)
        assert isinstance(result["nonce"], str)
        assert isinstance(result["ciphertext"], str)

        # Should be valid base64
        base64.b64decode(result["salt"])
        base64.b64decode(result["nonce"])
        base64.b64decode(result["ciphertext"])

    def test_decrypt_from_dict(self):
        """Should decrypt from dict format."""
        content = "Secret"
        passphrase = "password"

        encrypted_dict = encrypt_entry_to_dict(content, passphrase)
        decrypted = decrypt_entry_from_dict(encrypted_dict, passphrase)

        assert decrypted == content

    def test_decrypt_from_dict_invalid_format(self):
        """Should raise ValueError for invalid dict format."""
        with pytest.raises(ValueError, match="Invalid encrypted data format"):
            decrypt_entry_from_dict({"invalid": "format"}, "password")

    def test_decrypt_from_dict_invalid_base64(self):
        """Should raise ValueError for invalid base64."""
        bad_dict = {
            "salt": "not-valid-base64!!!",
            "nonce": "also-invalid",
            "ciphertext": "nope",
        }

        with pytest.raises(ValueError, match="Invalid encrypted data format"):
            decrypt_entry_from_dict(bad_dict, "password")
