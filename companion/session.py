"""Session management for passphrase caching.

Caches passphrase for the duration of the CLI session to avoid
repeated prompts while maintaining security.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PassphraseSession:
    """Manages passphrase caching for a CLI session."""

    def __init__(self) -> None:
        """Initialize empty passphrase cache."""
        self._passphrase: Optional[str] = None

    def set_passphrase(self, passphrase: str) -> None:
        """Cache passphrase for session.

        Args:
            passphrase: Passphrase to cache
        """
        self._passphrase = passphrase
        logger.debug("Passphrase cached for session")

    def get_passphrase(self) -> Optional[str]:
        """Get cached passphrase.

        Returns:
            Cached passphrase or None if not set
        """
        return self._passphrase

    def clear(self) -> None:
        """Clear cached passphrase."""
        self._passphrase = None
        logger.debug("Passphrase cache cleared")

    def has_passphrase(self) -> bool:
        """Check if passphrase is cached.

        Returns:
            True if passphrase is cached
        """
        return self._passphrase is not None


# Global session instance
_session = PassphraseSession()


def get_session() -> PassphraseSession:
    """Get global passphrase session.

    Returns:
        Global PassphraseSession instance
    """
    return _session
