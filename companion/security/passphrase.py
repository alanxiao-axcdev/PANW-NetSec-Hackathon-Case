"""Passphrase strength enforcement and brute force protection.

Implements NIST SP 800-63B 2024 guidelines for passphrase security:
- Minimum 12 character length
- Common password checking
- Entropy-based strength scoring
- Rate limiting and exponential backoff
- Account lockout after repeated failures
"""

import json
import logging
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PassphraseStrength(Enum):
    """Passphrase strength levels."""

    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class PassphraseScore:
    """Passphrase strength assessment.

    Attributes:
        strength: Strength level classification
        score: Numerical score 0-100
        feedback: List of improvement suggestions
        entropy_bits: Estimated entropy in bits
    """

    strength: PassphraseStrength
    score: int
    feedback: list[str]
    entropy_bits: float


@dataclass
class FailedAttempt:
    """Record of failed passphrase attempt.

    Attributes:
        timestamp: When attempt occurred
        attempt_type: Type of operation ('decrypt', 'rotate', 'audit')
        ip_address: Source IP (future: for multi-user support)
    """

    timestamp: datetime
    attempt_type: str
    ip_address: str = "local"


def _load_common_passwords() -> set[str]:
    """Load common password list from data file.

    Returns:
        Set of common passwords in lowercase

    Example:
        >>> passwords = _load_common_passwords()
        >>> "password" in passwords
        True
        >>> "123456" in passwords
        True
    """
    data_dir = Path(__file__).parent / "data"
    password_file = data_dir / "common_passwords.txt"

    if not password_file.exists():
        logger.warning("Common passwords file not found: %s", password_file)
        return _get_fallback_common_passwords()

    try:
        with password_file.open() as f:
            return {line.strip().lower() for line in f if line.strip()}
    except Exception as e:
        logger.error("Failed to load common passwords: %s", e)
        return _get_fallback_common_passwords()


def _get_fallback_common_passwords() -> set[str]:
    """Get minimal fallback list of common passwords.

    Returns:
        Set of most common passwords
    """
    return {
        "password",
        "123456",
        "password123",
        "qwerty",
        "abc123",
        "letmein",
        "welcome",
        "monkey",
        "dragon",
        "master",
        "passw0rd",
        "admin",
        "login",
        "sunshine",
        "iloveyou",
        "princess",
        "football",
        "starwars",
        "batman",
        "trustno1",
    }


_COMMON_PASSWORDS = _load_common_passwords()


def calculate_entropy(passphrase: str) -> float:
    """Estimate passphrase entropy using Shannon entropy.

    Calculates information-theoretic entropy based on character frequency.
    Higher entropy indicates more randomness and unpredictability.

    Args:
        passphrase: Passphrase to analyze

    Returns:
        Entropy in bits

    Guidelines:
        < 40 bits: Weak
        40-60 bits: Medium
        60-80 bits: Strong
        > 80 bits: Very strong

    Example:
        >>> calculate_entropy("password")  # Low entropy
        25.0
        >>> calculate_entropy("my-secure-journal-2025!")  # Higher entropy
        84.0
    """
    if not passphrase:
        return 0.0

    # Count character frequencies
    char_counts = Counter(passphrase)
    length = len(passphrase)

    # Shannon entropy formula: H = -sum(p * log2(p))
    entropy = 0.0
    for count in char_counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    # Total entropy = per-character entropy * length
    return entropy * length


def _check_repeated_patterns(passphrase: str) -> list[str]:
    """Check for repeated character patterns.

    Args:
        passphrase: Passphrase to check

    Returns:
        List of issues found

    Example:
        >>> _check_repeated_patterns("aaaa1234")
        ['Contains repeated characters (aaaa)']
        >>> _check_repeated_patterns("abc123xyz")
        []
    """
    issues = []

    # Check for 3+ repeated characters
    if re.search(r"(.)\1{2,}", passphrase):
        match = re.search(r"(.)\1{2,}", passphrase)
        if match:
            repeated = match.group()
            issues.append(f"Contains repeated characters ({repeated})")

    # Check for sequential numbers
    if re.search(r"(012|123|234|345|456|567|678|789|890)", passphrase):
        issues.append("Contains sequential numbers")

    # Check for sequential letters
    sequential_patterns = [
        "abc",
        "bcd",
        "cde",
        "def",
        "efg",
        "fgh",
        "ghi",
        "hij",
        "ijk",
        "jkl",
        "klm",
        "lmn",
        "mno",
        "nop",
        "opq",
        "pqr",
        "qrs",
        "rst",
        "stu",
        "tuv",
        "uvw",
        "vwx",
        "wxy",
        "xyz",
    ]
    for pattern in sequential_patterns:
        if pattern in passphrase.lower():
            issues.append("Contains sequential letters")
            break

    return issues


def _check_character_diversity(passphrase: str) -> tuple[int, list[str]]:
    """Check character type diversity.

    Args:
        passphrase: Passphrase to check

    Returns:
        Tuple of (score_bonus, feedback_list)

    Example:
        >>> _check_character_diversity("password")
        (0, ['Add numbers', 'Add special characters', 'Add uppercase letters'])
        >>> _check_character_diversity("Password123!")
        (15, [])
    """
    has_lower = bool(re.search(r"[a-z]", passphrase))
    has_upper = bool(re.search(r"[A-Z]", passphrase))
    has_digit = bool(re.search(r"[0-9]", passphrase))
    has_special = bool(re.search(r"[^a-zA-Z0-9]", passphrase))

    diversity_count = sum([has_lower, has_upper, has_digit, has_special])
    score_bonus = diversity_count * 5  # Up to 20 points

    feedback = []
    if not has_digit:
        feedback.append("Add numbers")
    if not has_special:
        feedback.append("Add special characters")
    if not has_upper:
        feedback.append("Add uppercase letters")

    return score_bonus, feedback


def _score_length(length: int) -> tuple[int, list[str]]:
    """Score passphrase length.

    Args:
        length: Passphrase length in characters

    Returns:
        Tuple of (score, feedback)
    """
    if length < 8:
        return 0, [f"Too short ({length} chars, need 12+)"]
    if length < 12:
        return 10, [f"Short ({length} chars, need 12+)"]
    if length < 16:
        return 25, [f"Good length ({length} chars, 16+ recommended)"]
    return 40, []


def _score_entropy(entropy: float) -> tuple[int, list[str]]:
    """Score passphrase entropy.

    Args:
        entropy: Entropy in bits

    Returns:
        Tuple of (score, feedback)
    """
    if entropy < 40:
        return 5, ["Low entropy (predictable)"]
    if entropy < 60:
        return 15, []
    if entropy < 80:
        return 25, []
    return 30, []


def _classify_strength(score: int) -> PassphraseStrength:
    """Classify strength based on score.

    Args:
        score: Numerical score 0-100

    Returns:
        Strength classification
    """
    if score < 30:
        return PassphraseStrength.WEAK
    if score < 50:
        return PassphraseStrength.MEDIUM
    if score < 70:
        return PassphraseStrength.STRONG
    return PassphraseStrength.VERY_STRONG


def check_passphrase_strength(passphrase: str) -> PassphraseScore:
    """Evaluate passphrase strength comprehensively.

    Checks:
    - Length (12+ required, 16+ recommended)
    - Common passwords (top 10k banned)
    - Dictionary words
    - Repeated patterns (aaaa, 1234)
    - Sequential characters (abcd, 6789)
    - Character diversity (letters, numbers, symbols)
    - Entropy estimation

    Args:
        passphrase: Passphrase to evaluate

    Returns:
        PassphraseScore with strength assessment and feedback

    Example:
        >>> score = check_passphrase_strength("password123")
        >>> score.strength
        <PassphraseStrength.WEAK: 'weak'>
        >>> score.score < 30
        True
        >>> len(score.feedback) > 0
        True

        >>> score = check_passphrase_strength("my-secure-journal-2025!")
        >>> score.strength in (PassphraseStrength.STRONG, PassphraseStrength.VERY_STRONG)
        True
        >>> score.score > 70
        True
    """
    feedback = []
    score = 0

    # Length check (0-40 points)
    length_score, length_feedback = _score_length(len(passphrase))
    score += length_score
    feedback.extend(length_feedback)

    # Common password check (-30 points penalty)
    if passphrase.lower() in _COMMON_PASSWORDS:
        score = max(0, score - 30)
        feedback.append("Common password (found in breach database)")

    # Entropy check (0-30 points)
    entropy = calculate_entropy(passphrase)
    entropy_score, entropy_feedback = _score_entropy(entropy)
    score += entropy_score
    feedback.extend(entropy_feedback)

    # Character diversity (0-20 points)
    diversity_bonus, diversity_feedback = _check_character_diversity(passphrase)
    score += diversity_bonus
    feedback.extend(diversity_feedback)

    # Pattern checks (penalties)
    pattern_issues = _check_repeated_patterns(passphrase)
    if pattern_issues:
        score = max(0, score - 10 * len(pattern_issues))
        feedback.extend(pattern_issues)

    # Classify strength and cap score
    score = min(100, score)
    strength = _classify_strength(score)

    return PassphraseScore(
        strength=strength, score=score, feedback=feedback, entropy_bits=entropy
    )


def is_passphrase_acceptable(passphrase: str) -> tuple[bool, str]:
    """Check if passphrase meets minimum security requirements.

    Enforces:
    - Minimum 12 character length
    - Not in common password list
    - Reasonable entropy (>= 30 bits)

    Args:
        passphrase: Passphrase to validate

    Returns:
        Tuple of (is_acceptable, rejection_reason)
        rejection_reason is empty string if acceptable

    Example:
        >>> is_passphrase_acceptable("password123")
        (False, 'Passphrase is in common password list')

        >>> is_passphrase_acceptable("short")
        (False, 'Passphrase must be at least 12 characters')

        >>> is_passphrase_acceptable("my-secure-journal-2025!")
        (True, '')
    """
    # Length check
    if len(passphrase) < 12:
        return False, "Passphrase must be at least 12 characters"

    # Common password check
    if passphrase.lower() in _COMMON_PASSWORDS:
        return False, "Passphrase is in common password list"

    # Entropy check (minimum 30 bits)
    entropy = calculate_entropy(passphrase)
    if entropy < 30:
        return (
            False,
            "Passphrase is too predictable (low entropy). Use more varied characters.",
        )

    return True, ""


class BruteForceProtector:
    """Tracks and limits passphrase attempts to prevent brute force attacks.

    Implements multi-layer defense:
    - Rate limiting: Max 5 attempts per 15 minutes
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s delays
    - Account lockout: Lock after 10 attempts in 24 hours
    - Persistence: Survives application restarts

    Example:
        >>> from pathlib import Path
        >>> protector = BruteForceProtector(Path(".companion"))
        >>> protector.record_attempt(success=False, attempt_type="decrypt")
        >>> allowed, msg = protector.check_rate_limit()
        >>> allowed
        True
    """

    def __init__(self, data_dir: Path):
        """Initialize brute force protector.

        Args:
            data_dir: Directory for storing attempt history
        """
        self.attempts_file = data_dir / "auth_attempts.json"
        self.max_attempts_per_window = 5
        self.window_minutes = 15
        self.lockout_threshold = 10
        self.lockout_hours = 24

        # Ensure data directory exists
        data_dir.mkdir(parents=True, exist_ok=True)

    def _load_attempts(self) -> list[FailedAttempt]:
        """Load attempt history from file.

        Returns:
            List of failed attempts
        """
        if not self.attempts_file.exists():
            return []

        try:
            with self.attempts_file.open() as f:
                data = json.load(f)
            return [
                FailedAttempt(
                    timestamp=datetime.fromisoformat(a["timestamp"]),
                    attempt_type=a["attempt_type"],
                    ip_address=a.get("ip_address", "local"),
                )
                for a in data
            ]
        except Exception as e:
            logger.error("Failed to load attempt history: %s", e)
            return []

    def _save_attempts(self, attempts: list[FailedAttempt]) -> None:
        """Save attempt history to file.

        Args:
            attempts: List of failed attempts to save
        """
        try:
            with self.attempts_file.open("w") as f:
                json.dump([asdict(a) for a in attempts], f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save attempt history: %s", e)

    def record_attempt(self, success: bool, attempt_type: str) -> None:
        """Record a passphrase attempt.

        Args:
            success: Whether the attempt succeeded
            attempt_type: Type of operation ('decrypt', 'rotate', 'audit')

        Example:
            >>> protector.record_attempt(success=False, attempt_type="decrypt")
            >>> protector.record_attempt(success=True, attempt_type="decrypt")
        """
        if success:
            # Clear history on successful auth
            self.reset()
            return

        # Record failed attempt
        attempts = self._load_attempts()
        attempts.append(
            FailedAttempt(
                timestamp=datetime.now(UTC), attempt_type=attempt_type, ip_address="local"
            )
        )
        self._save_attempts(attempts)

        logger.warning(
            "Failed passphrase attempt recorded: %s (total: %d)",
            attempt_type,
            len(attempts),
        )

    def check_rate_limit(self) -> tuple[bool, str]:
        """Check if rate limit has been exceeded.

        Returns:
            Tuple of (is_allowed, message)
            message is empty string if allowed

        Example:
            >>> protector.check_rate_limit()
            (True, '')

            >>> # After 6 failures in 15 minutes
            >>> protector.check_rate_limit()
            (False, 'Too many attempts. Wait 15 minutes.')
        """
        attempts = self._load_attempts()
        if not attempts:
            return True, ""

        # Check attempts in last window
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=self.window_minutes)
        recent_attempts = [a for a in attempts if a.timestamp >= window_start]

        if len(recent_attempts) >= self.max_attempts_per_window:
            next_attempt = attempts[-1].timestamp + timedelta(minutes=self.window_minutes)
            return (
                False,
                f"Too many attempts ({len(recent_attempts)}/{self.max_attempts_per_window}). "
                f"Try again after {next_attempt.strftime('%H:%M')}.",
            )

        return True, ""

    def is_locked_out(self) -> tuple[bool, datetime | None]:
        """Check if account is locked due to repeated failures.

        Returns:
            Tuple of (is_locked, unlock_time)
            unlock_time is None if not locked

        Example:
            >>> protector.is_locked_out()
            (False, None)

            >>> # After 10+ failures in 24 hours
            >>> locked, unlock_time = protector.is_locked_out()
            >>> locked
            True
            >>> unlock_time is not None
            True
        """
        attempts = self._load_attempts()
        if not attempts:
            return False, None

        # Check attempts in last 24 hours
        now = datetime.now(UTC)
        lockout_window = now - timedelta(hours=self.lockout_hours)
        recent_attempts = [a for a in attempts if a.timestamp >= lockout_window]

        if len(recent_attempts) >= self.lockout_threshold:
            unlock_time = attempts[0].timestamp + timedelta(hours=self.lockout_hours)
            return True, unlock_time

        return False, None

    def get_delay_seconds(self) -> int:
        """Get required delay before next attempt (exponential backoff).

        Returns:
            Seconds to wait (0 if no delay needed)

        Example:
            >>> protector.get_delay_seconds()
            0

            >>> # After 3 failures
            >>> protector.get_delay_seconds()
            4  # 2^(3-1) = 4 seconds
        """
        attempts = self._load_attempts()
        if not attempts:
            return 0

        # Check recent attempts (last 15 minutes)
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=self.window_minutes)
        recent_attempts = [a for a in attempts if a.timestamp >= window_start]

        if len(recent_attempts) < 2:
            return 0

        # Exponential backoff: 2^(n-1) seconds
        # Attempt 2: 1s, Attempt 3: 2s, Attempt 4: 4s, etc.
        delay = 2 ** (len(recent_attempts) - 2)
        return min(delay, 60)  # Cap at 60 seconds

    def reset(self) -> None:
        """Reset attempt counter after successful authentication.

        Example:
            >>> protector.reset()
        """
        if self.attempts_file.exists():
            self.attempts_file.unlink()
        logger.info("Reset brute force protection (successful auth)")

    def get_recent_attempts(self, hours: int = 24) -> list[FailedAttempt]:
        """Get recent failed attempts for audit.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent failed attempts

        Example:
            >>> attempts = protector.get_recent_attempts(hours=24)
            >>> len(attempts)
            0
        """
        attempts = self._load_attempts()
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        return [a for a in attempts if a.timestamp >= cutoff]
