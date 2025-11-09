"""AES-256-GCM encryption for journal entries.

Implements authenticated encryption for protecting journal entries at rest.
Uses PBKDF2 for key derivation with OWASP-recommended iteration count.
"""

import base64
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from companion.models import RotationMetadata, RotationResult

logger = logging.getLogger(__name__)

# OWASP recommendation for PBKDF2 iterations (2023)
PBKDF2_ITERATIONS = 600_000
KEY_LENGTH = 32  # 256 bits for AES-256
SALT_LENGTH = 16  # 128 bits
NONCE_LENGTH = 12  # 96 bits for GCM


class EncryptedData(NamedTuple):
    """Encrypted data with metadata.

    Attributes:
        salt: Random salt used for key derivation
        nonce: Random nonce used for encryption
        ciphertext: Encrypted data
        tag: Authentication tag (included in ciphertext for GCM)
    """

    salt: bytes
    nonce: bytes
    ciphertext: bytes


def derive_key(passphrase: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Derive encryption key from passphrase using PBKDF2.

    Uses PBKDF2-HMAC-SHA256 with high iteration count to make
    brute-force attacks computationally expensive.

    Args:
        passphrase: User's passphrase
        salt: Random salt (should be unique per entry)
        iterations: Number of PBKDF2 iterations (default: 600,000)

    Returns:
        32-byte derived key suitable for AES-256

    Example:
        >>> salt = os.urandom(16)
        >>> key = derive_key("my secure passphrase", salt)
        >>> len(key)
        32
    """
    if not passphrase:
        msg = "Passphrase cannot be empty"
        raise ValueError(msg)

    if len(salt) < SALT_LENGTH:
        msg = f"Salt must be at least {SALT_LENGTH} bytes"
        raise ValueError(msg)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )

    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_entry(content: str, passphrase: str) -> bytes:
    """Encrypt journal entry content.

    Uses AES-256-GCM for authenticated encryption with random salt and nonce.
    The authentication tag ensures data hasn't been tampered with.

    Args:
        content: Plain text journal entry content
        passphrase: User's encryption passphrase

    Returns:
        Encrypted data as bytes (format: salt || nonce || ciphertext+tag)

    Raises:
        ValueError: If content or passphrase is empty

    Example:
        >>> encrypted = encrypt_entry("My private thoughts", "secure123")
        >>> len(encrypted) > 0
        True
    """
    if not content:
        msg = "Content cannot be empty"
        raise ValueError(msg)

    if not passphrase:
        msg = "Passphrase cannot be empty"
        raise ValueError(msg)

    # Generate random salt and nonce
    salt = os.urandom(SALT_LENGTH)
    nonce = os.urandom(NONCE_LENGTH)

    # Derive key from passphrase
    key = derive_key(passphrase, salt)

    # Encrypt with AES-256-GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, content.encode("utf-8"), None)

    # Package: salt || nonce || ciphertext (includes auth tag)
    encrypted = salt + nonce + ciphertext

    logger.debug(
        "Encrypted entry: %d bytes plaintext -> %d bytes ciphertext",
        len(content),
        len(ciphertext),
    )

    return encrypted


def decrypt_entry(encrypted: bytes, passphrase: str) -> str:
    """Decrypt journal entry content.

    Verifies authentication tag to detect tampering before decryption.

    Args:
        encrypted: Encrypted data (format: salt || nonce || ciphertext+tag)
        passphrase: User's decryption passphrase

    Returns:
        Decrypted plain text content

    Raises:
        ValueError: If encrypted data is invalid or passphrase is wrong
        cryptography.exceptions.InvalidTag: If authentication fails (tampering detected)

    Example:
        >>> encrypted = encrypt_entry("Secret", "pass123")
        >>> decrypted = decrypt_entry(encrypted, "pass123")
        >>> decrypted
        'Secret'
    """
    if not encrypted:
        msg = "Encrypted data cannot be empty"
        raise ValueError(msg)

    if not passphrase:
        msg = "Passphrase cannot be empty"
        raise ValueError(msg)

    # Parse encrypted data
    min_length = SALT_LENGTH + NONCE_LENGTH + 16  # 16 bytes min ciphertext + tag
    if len(encrypted) < min_length:
        msg = f"Encrypted data too short (minimum {min_length} bytes)"
        raise ValueError(msg)

    salt = encrypted[:SALT_LENGTH]
    nonce = encrypted[SALT_LENGTH : SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted[SALT_LENGTH + NONCE_LENGTH :]

    # Derive key from passphrase
    try:
        key = derive_key(passphrase, salt)
    except Exception as e:
        msg = f"Key derivation failed: {e}"
        raise ValueError(msg) from e

    # Decrypt and verify authentication tag
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        # Invalid tag means tampering or wrong passphrase
        msg = "Decryption failed (wrong passphrase or tampered data)"
        raise ValueError(msg) from e

    try:
        content = plaintext.decode("utf-8")
    except UnicodeDecodeError as e:
        msg = "Decrypted data is not valid UTF-8"
        raise ValueError(msg) from e

    logger.debug(
        "Decrypted entry: %d bytes ciphertext -> %d bytes plaintext",
        len(ciphertext),
        len(content),
    )

    return content


def encrypt_entry_to_dict(content: str, passphrase: str) -> dict[str, str]:
    """Encrypt entry and return as dictionary for JSON storage.

    Args:
        content: Plain text content to encrypt
        passphrase: Encryption passphrase

    Returns:
        Dictionary with base64-encoded salt, nonce, and ciphertext

    Example:
        >>> data = encrypt_entry_to_dict("Secret", "pass123")
        >>> set(data.keys())
        {'salt', 'nonce', 'ciphertext'}
    """
    encrypted = encrypt_entry(content, passphrase)

    salt = encrypted[:SALT_LENGTH]
    nonce = encrypted[SALT_LENGTH : SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted[SALT_LENGTH + NONCE_LENGTH :]

    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_entry_from_dict(data: dict[str, str], passphrase: str) -> str:
    """Decrypt entry from dictionary format.

    Args:
        data: Dictionary with base64-encoded salt, nonce, and ciphertext
        passphrase: Decryption passphrase

    Returns:
        Decrypted plain text content

    Example:
        >>> encrypted_dict = encrypt_entry_to_dict("Secret", "pass123")
        >>> decrypted = decrypt_entry_from_dict(encrypted_dict, "pass123")
        >>> decrypted
        'Secret'
    """
    try:
        salt = base64.b64decode(data["salt"])
        nonce = base64.b64decode(data["nonce"])
        ciphertext = base64.b64decode(data["ciphertext"])
    except (KeyError, ValueError) as e:
        msg = f"Invalid encrypted data format: {e}"
        raise ValueError(msg) from e

    encrypted = salt + nonce + ciphertext
    return decrypt_entry(encrypted, passphrase)


def verify_passphrase(passphrase: str, encrypted_file: Path) -> bool:
    """Test if passphrase can decrypt a file.

    Args:
        passphrase: Passphrase to verify
        encrypted_file: Sample encrypted file to test (JSON format)

    Returns:
        True if passphrase works, False otherwise

    Example:
        >>> from pathlib import Path
        >>> # Create test file
        >>> test_file = Path("test.json")
        >>> entry_dict = {"id": "test", "content": "test"}
        >>> encrypted = encrypt_full_entry_to_dict(entry_dict, "pass123")
        >>> import json
        >>> test_file.write_text(json.dumps(encrypted))
        >>> verify_passphrase("pass123", test_file)
        True
        >>> verify_passphrase("wrong", test_file)
        False
    """
    try:
        import json
        with open(encrypted_file) as f:
            data = json.load(f)
        # Try to decrypt - if passphrase is wrong, this will raise exception
        decrypt_full_entry_from_dict(data, passphrase)
        return True
    except Exception:
        return False


def rotate_keys(
    old_passphrase: str,
    new_passphrase: str,
    entries_dir: Path,
    backup_dir: Path | None = None,
) -> RotationResult:
    """Rotate encryption keys for all entries.

    Process:
    1. Verify old passphrase
    2. Create backup (optional)
    3. For each entry:
       - Decrypt with old passphrase
       - Re-encrypt with new passphrase
       - Atomic replace
    4. Update rotation metadata
    5. Return results

    Args:
        old_passphrase: Current passphrase
        new_passphrase: New passphrase
        entries_dir: Directory containing encrypted entries
        backup_dir: Optional backup location

    Returns:
        RotationResult with status and statistics

    Raises:
        ValueError: If old passphrase is incorrect

    Example:
        >>> from pathlib import Path
        >>> entries = Path("entries")
        >>> backup = Path("backup")
        >>> result = rotate_keys("old", "new", entries, backup)
        >>> result.success
        True
    """
    start_time = time.time()
    rotated = 0
    failed = 0
    errors = []

    # Get all encrypted entry files
    entry_files = list(entries_dir.glob("*.json"))

    if not entry_files:
        return RotationResult(
            success=True, entries_rotated=0, errors=["No encrypted entries found"]
        )

    # Verify old passphrase works
    if not verify_passphrase(old_passphrase, entry_files[0]):
        return RotationResult(
            success=False, entries_rotated=0, errors=["Old passphrase is incorrect"]
        )

    # Create backup if requested
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for entry_file in entry_files:
            shutil.copy2(entry_file, backup_dir / entry_file.name)
        logger.info("Created backup in %s", backup_dir)

    # Rotate each entry
    for entry_file in entry_files:
        try:
            # Read encrypted JSON data
            with open(entry_file) as f:
                old_encrypted_dict = json.load(f)

            # Decrypt with old passphrase (returns complete entry dict)
            decrypted_dict = decrypt_full_entry_from_dict(old_encrypted_dict, old_passphrase)

            # Re-encrypt with new passphrase
            new_encrypted_dict = encrypt_full_entry_to_dict(decrypted_dict, new_passphrase)

            # Atomic replace
            temp_file = entry_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(new_encrypted_dict, f, indent=2)
            temp_file.replace(entry_file)

            rotated += 1
            logger.debug("Rotated key for %s", entry_file.name)

        except Exception as e:
            failed += 1
            error_msg = f"{entry_file.name}: {e!s}"
            errors.append(error_msg)
            logger.error("Failed to rotate %s: %s", entry_file.name, e)

    duration = time.time() - start_time

    logger.info(
        "Key rotation complete: %d succeeded, %d failed in %.2fs",
        rotated,
        failed,
        duration,
    )

    return RotationResult(
        success=(failed == 0),
        entries_rotated=rotated,
        entries_failed=failed,
        errors=errors,
        duration_seconds=duration,
    )


def get_rotation_metadata(config_dir: Path) -> RotationMetadata | None:
    """Load rotation metadata from file.

    Args:
        config_dir: Configuration directory

    Returns:
        RotationMetadata if file exists, None otherwise

    Example:
        >>> from pathlib import Path
        >>> config = Path(".companion")
        >>> metadata = get_rotation_metadata(config)
        >>> metadata is None or isinstance(metadata, RotationMetadata)
        True
    """
    metadata_file = config_dir / "rotation_metadata.json"
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            data = json.load(f)
        return RotationMetadata(**data)
    except Exception as e:
        logger.error("Failed to load rotation metadata: %s", e)
        return None


def save_rotation_metadata(metadata: RotationMetadata, config_dir: Path) -> None:
    """Save rotation metadata to file.

    Args:
        metadata: Rotation metadata to save
        config_dir: Configuration directory

    Example:
        >>> from pathlib import Path
        >>> from datetime import datetime, timedelta
        >>> config = Path(".companion")
        >>> metadata = RotationMetadata(
        ...     last_rotation=datetime.now(),
        ...     rotation_interval_days=90,
        ...     next_rotation_due=datetime.now() + timedelta(days=90),
        ...     total_rotations=1
        ... )
        >>> save_rotation_metadata(metadata, config)
    """
    metadata_file = config_dir / "rotation_metadata.json"
    try:
        with open(metadata_file, "w") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, default=str)
        logger.info("Saved rotation metadata to %s", metadata_file)
    except Exception as e:
        logger.error("Failed to save rotation metadata: %s", e)


def should_rotate(config_dir: Path, rotation_interval_days: int = 90) -> bool:
    """Check if rotation is due.

    Args:
        config_dir: Configuration directory
        rotation_interval_days: Days between rotations (default: 90)

    Returns:
        True if rotation is due or overdue

    Example:
        >>> from pathlib import Path
        >>> config = Path(".companion")
        >>> should_rotate(config)  # Returns True if >90 days since last rotation
        False
    """
    metadata = get_rotation_metadata(config_dir)
    if not metadata:
        return False  # No previous rotation

    return datetime.now() >= metadata.next_rotation_due


def encrypt_full_entry_to_dict(entry_data: dict, passphrase: str) -> dict[str, str]:
    """Encrypt entire entry (all metadata and content) for JSON storage.

    Encrypts the complete entry dictionary as a single blob, preserving only
    the entry ID and encryption metadata fields needed for decryption.

    Args:
        entry_data: Complete entry dictionary to encrypt
        passphrase: Encryption passphrase

    Returns:
        Dictionary with only: id, encrypted, salt, nonce, ciphertext
        All other entry data is encrypted within ciphertext.

    Example:
        >>> entry = {"id": "123", "timestamp": "2025-01-01T00:00:00", "content": "secret", ...}
        >>> encrypted = encrypt_full_entry_to_dict(entry, "pass123")
        >>> set(encrypted.keys())
        {'id', 'encrypted', 'salt', 'nonce', 'ciphertext'}
    """
    # Extract ID (needed for file lookup)
    entry_id = entry_data.get("id")
    if not entry_id:
        msg = "Entry must have an 'id' field"
        raise ValueError(msg)

    # Encrypt entire entry as JSON
    entry_json = json.dumps(entry_data, ensure_ascii=False, default=str)
    encrypted = encrypt_entry(entry_json, passphrase)

    salt = encrypted[:SALT_LENGTH]
    nonce = encrypted[SALT_LENGTH : SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted[SALT_LENGTH + NONCE_LENGTH :]

    return {
        "id": entry_id,
        "encrypted": True,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_full_entry_from_dict(data: dict[str, str], passphrase: str) -> dict:
    """Decrypt full entry from dictionary format.

    Decrypts complete entry data that was encrypted with encrypt_full_entry_to_dict().

    Args:
        data: Dictionary with base64-encoded salt, nonce, and ciphertext
        passphrase: Decryption passphrase

    Returns:
        Complete decrypted entry dictionary with all metadata and content

    Example:
        >>> encrypted_dict = encrypt_full_entry_to_dict(entry, "pass123")
        >>> decrypted = decrypt_full_entry_from_dict(encrypted_dict, "pass123")
        >>> decrypted["content"]
        'secret'
    """
    try:
        salt = base64.b64decode(data["salt"])
        nonce = base64.b64decode(data["nonce"])
        ciphertext = base64.b64decode(data["ciphertext"])
    except (KeyError, ValueError) as e:
        msg = f"Invalid encrypted data format: {e}"
        raise ValueError(msg) from e

    encrypted = salt + nonce + ciphertext
    entry_json = decrypt_entry(encrypted, passphrase)

    try:
        entry_data = json.loads(entry_json)
    except json.JSONDecodeError as e:
        msg = f"Decrypted data is not valid JSON: {e}"
        raise ValueError(msg) from e

    return entry_data
