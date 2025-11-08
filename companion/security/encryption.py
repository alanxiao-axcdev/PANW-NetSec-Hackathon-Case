"""AES-256-GCM encryption for journal entries.

Implements authenticated encryption for protecting journal entries at rest.
Uses PBKDF2 for key derivation with OWASP-recommended iteration count.
"""

import base64
import logging
import os
from typing import NamedTuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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
