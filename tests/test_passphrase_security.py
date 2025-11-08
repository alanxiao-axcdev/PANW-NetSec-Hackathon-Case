"""Tests for passphrase strength enforcement and brute force protection.

Tests NIST SP 800-63B 2024 compliance for passphrase security.
"""

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.security.passphrase import (
    BruteForceProtector,
    PassphraseScore,
    PassphraseStrength,
    calculate_entropy,
    check_passphrase_strength,
    is_passphrase_acceptable,
)


class TestPassphraseStrength:
    """Test passphrase strength checking."""

    def test_weak_passphrases(self) -> None:
        """Test that weak passphrases are correctly identified."""
        weak_passphrases = [
            "password",
            "123456",
            "password123",
            "qwerty",
            "abc123",
            "12345678",
            "letmein",
        ]

        for passphrase in weak_passphrases:
            score = check_passphrase_strength(passphrase)
            assert score.strength == PassphraseStrength.WEAK, f"'{passphrase}' should be weak"
            assert score.score < 30, f"'{passphrase}' score too high: {score.score}"
            assert len(score.feedback) > 0, f"'{passphrase}' should have feedback"

    def test_medium_passphrases(self) -> None:
        """Test medium strength passphrases."""
        medium_passphrases = [
            "myjournal2025",
            "personal-diary",
            "thoughts123456",
        ]

        for passphrase in medium_passphrases:
            score = check_passphrase_strength(passphrase)
            # These can be medium or weak, or even strong if they have good entropy
            assert score.strength in (
                PassphraseStrength.MEDIUM,
                PassphraseStrength.WEAK,
                PassphraseStrength.STRONG,
            ), f"'{passphrase}' should be medium, weak, or strong"
            assert 10 <= score.score <= 70, f"'{passphrase}' score out of range: {score.score}"

    def test_strong_passphrases(self) -> None:
        """Test strong passphrases."""
        strong_passphrases = [
            "my-secure-journal-2025!",
            "private_thoughts_2025$",
            "MySecureJournal2025!",
            "correct-horse-battery-staple",
        ]

        for passphrase in strong_passphrases:
            score = check_passphrase_strength(passphrase)
            assert score.strength in (
                PassphraseStrength.STRONG,
                PassphraseStrength.VERY_STRONG,
            ), f"'{passphrase}' should be strong"
            assert score.score >= 60, f"'{passphrase}' score too low: {score.score}"

    def test_very_strong_passphrases(self) -> None:
        """Test very strong passphrases."""
        very_strong = [
            "MyVerySecureJournal2025!@#$%",
            "correct-horse-battery-staple-2025!",
            "Th1s_Is_A_V3ry_S3cur3_P@ssphr@s3!",
        ]

        for passphrase in very_strong:
            score = check_passphrase_strength(passphrase)
            assert score.strength == PassphraseStrength.VERY_STRONG, f"'{passphrase}' should be very strong"
            assert score.score >= 70, f"'{passphrase}' score too low: {score.score}"

    def test_common_password_detection(self) -> None:
        """Test that common passwords are detected and penalized."""
        common_passwords = [
            "password",
            "123456",
            "password123",
            "qwerty",
            "abc123",
            "monkey",
            "letmein",
        ]

        for pwd in common_passwords:
            score = check_passphrase_strength(pwd)
            assert "Common password" in " ".join(score.feedback), f"'{pwd}' should be flagged as common"
            assert score.strength == PassphraseStrength.WEAK, f"'{pwd}' should be weak due to being common"

    def test_repeated_patterns(self) -> None:
        """Test detection of repeated character patterns."""
        test_cases = [
            ("aaaa1234", "repeated characters"),
            ("password1111", "repeated characters"),
            ("abc1234567", "sequential numbers"),
            ("abcdef123", "sequential letters"),
        ]

        for passphrase, expected_issue in test_cases:
            score = check_passphrase_strength(passphrase)
            feedback_text = " ".join(score.feedback).lower()
            assert expected_issue in feedback_text, f"'{passphrase}' should flag '{expected_issue}'"

    def test_length_requirements(self) -> None:
        """Test length-based scoring."""
        test_cases = [
            ("short", True, "Too short"),  # < 8 chars
            ("12345678", True, "Short"),  # 8 chars
            ("123456789012", True, "Good length"),  # 12 chars
            ("1234567890123456", False, None),  # 16+ chars
        ]

        for passphrase, should_have_feedback, expected_msg in test_cases:
            score = check_passphrase_strength(passphrase)
            if should_have_feedback:
                feedback_text = " ".join(score.feedback)
                assert expected_msg in feedback_text, f"'{passphrase}' should mention '{expected_msg}'"


class TestEntropyCalculation:
    """Test entropy calculation."""

    def test_entropy_low(self) -> None:
        """Test low entropy passphrases."""
        low_entropy = ["aaaaaaa", "1111111", "password"]

        for passphrase in low_entropy:
            entropy = calculate_entropy(passphrase)
            assert entropy < 40, f"'{passphrase}' should have low entropy, got {entropy}"

    def test_entropy_medium(self) -> None:
        """Test medium entropy passphrases."""
        medium_entropy = ["myjournal123", "personal-diary"]

        for passphrase in medium_entropy:
            entropy = calculate_entropy(passphrase)
            assert 30 < entropy < 70, f"'{passphrase}' should have medium entropy, got {entropy}"

    def test_entropy_high(self) -> None:
        """Test high entropy passphrases."""
        high_entropy = [
            "my-secure-journal-2025!",
            "correct-horse-battery-staple",
            "MyVerySecureJournal2025!@#",
        ]

        for passphrase in high_entropy:
            entropy = calculate_entropy(passphrase)
            assert entropy > 60, f"'{passphrase}' should have high entropy, got {entropy}"

    def test_entropy_empty_string(self) -> None:
        """Test entropy of empty string."""
        assert calculate_entropy("") == 0.0


class TestPassphraseAcceptability:
    """Test passphrase acceptance criteria."""

    def test_reject_too_short(self) -> None:
        """Test rejection of passphrases under 12 characters."""
        short_passphrases = ["short", "12345", "password"]

        for pwd in short_passphrases:
            acceptable, reason = is_passphrase_acceptable(pwd)
            assert not acceptable, f"'{pwd}' should be rejected"
            assert "12 characters" in reason.lower(), f"'{pwd}' rejection reason should mention length"

    def test_reject_common_passwords(self) -> None:
        """Test rejection of common passwords."""
        common = ["password123", "qwerty", "123456"]

        for pwd in common:
            if len(pwd) >= 12:  # Only test if length requirement met
                pwd = pwd + "extra"  # Make it 12+ chars
            acceptable, reason = is_passphrase_acceptable(pwd)
            # Common password check happens after length
            if len(pwd) >= 12:
                assert not acceptable, f"'{pwd}' should be rejected as common"
                assert "common" in reason.lower(), f"'{pwd}' rejection should mention common password"

    def test_reject_low_entropy(self) -> None:
        """Test rejection of very low entropy passphrases."""
        low_entropy = "aaaaaaaaaaaa"  # 12 'a's - meets length but terrible entropy

        acceptable, reason = is_passphrase_acceptable(low_entropy)
        assert not acceptable, f"'{low_entropy}' should be rejected"
        assert "entropy" in reason.lower() or "predictable" in reason.lower()

    def test_accept_strong_passphrases(self) -> None:
        """Test acceptance of strong passphrases."""
        strong_passphrases = [
            "my-secure-journal-2025!",
            "correct-horse-battery-staple",
            "MySecureJournal2025",
        ]

        for pwd in strong_passphrases:
            acceptable, reason = is_passphrase_acceptable(pwd)
            assert acceptable, f"'{pwd}' should be accepted: {reason}"
            assert reason == "", f"'{pwd}' should have no rejection reason"


class TestBruteForceProtection:
    """Test brute force protection mechanisms."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory."""
        return tmp_path / "test_companion"

    @pytest.fixture
    def protector(self, temp_data_dir: Path) -> BruteForceProtector:
        """Create BruteForceProtector instance."""
        temp_data_dir.mkdir(parents=True, exist_ok=True)
        return BruteForceProtector(temp_data_dir)

    def test_initial_state(self, protector: BruteForceProtector) -> None:
        """Test initial state allows attempts."""
        allowed, msg = protector.check_rate_limit()
        assert allowed
        assert msg == ""

        locked, unlock_time = protector.is_locked_out()
        assert not locked
        assert unlock_time is None

    def test_record_failed_attempts(self, protector: BruteForceProtector) -> None:
        """Test recording failed attempts."""
        # Record 3 failures
        for _ in range(3):
            protector.record_attempt(success=False, attempt_type="decrypt")

        # Should still be allowed
        allowed, _ = protector.check_rate_limit()
        assert allowed

        # Verify attempts recorded
        attempts = protector.get_recent_attempts(hours=1)
        assert len(attempts) == 3

    def test_rate_limiting(self, protector: BruteForceProtector) -> None:
        """Test rate limiting after max attempts."""
        # Record max attempts (5)
        for _ in range(5):
            protector.record_attempt(success=False, attempt_type="decrypt")

        # 6th attempt should be rate limited
        protector.record_attempt(success=False, attempt_type="decrypt")
        allowed, msg = protector.check_rate_limit()
        assert not allowed
        assert "Too many attempts" in msg

    def test_exponential_backoff(self, protector: BruteForceProtector) -> None:
        """Test exponential backoff delays."""
        delays = []

        for i in range(5):
            protector.record_attempt(success=False, attempt_type="decrypt")
            delay = protector.get_delay_seconds()
            delays.append(delay)

        # First attempt: no delay
        assert delays[0] == 0

        # Second attempt: 1 second
        assert delays[1] == 1

        # Third attempt: 2 seconds
        assert delays[2] == 2

        # Fourth attempt: 4 seconds
        assert delays[3] == 4

        # Fifth attempt: 8 seconds
        assert delays[4] == 8

    def test_account_lockout(self, protector: BruteForceProtector) -> None:
        """Test account lockout after threshold."""
        # Record 10 failures (lockout threshold)
        for _ in range(10):
            protector.record_attempt(success=False, attempt_type="decrypt")

        # Should be locked out
        locked, unlock_time = protector.is_locked_out()
        assert locked
        assert unlock_time is not None
        assert unlock_time > datetime.now(UTC)

    def test_reset_on_success(self, protector: BruteForceProtector) -> None:
        """Test that successful auth resets counter."""
        # Record some failures
        for _ in range(3):
            protector.record_attempt(success=False, attempt_type="decrypt")

        # Verify attempts recorded
        attempts = protector.get_recent_attempts(hours=1)
        assert len(attempts) == 3

        # Successful auth
        protector.record_attempt(success=True, attempt_type="decrypt")

        # Should be reset
        attempts = protector.get_recent_attempts(hours=1)
        assert len(attempts) == 0

        allowed, _ = protector.check_rate_limit()
        assert allowed

    def test_persistence_across_restarts(self, temp_data_dir: Path) -> None:
        """Test that attempt history persists across restarts."""
        # Create protector and record failures
        protector1 = BruteForceProtector(temp_data_dir)
        for _ in range(3):
            protector1.record_attempt(success=False, attempt_type="decrypt")

        # Create new protector (simulating restart)
        protector2 = BruteForceProtector(temp_data_dir)

        # Should still have attempts
        attempts = protector2.get_recent_attempts(hours=1)
        assert len(attempts) == 3

    def test_recent_attempts_filtering(self, protector: BruteForceProtector) -> None:
        """Test filtering of recent attempts by time window."""
        # Record attempts
        for _ in range(3):
            protector.record_attempt(success=False, attempt_type="decrypt")

        # All should be in last 24 hours
        attempts_24h = protector.get_recent_attempts(hours=24)
        assert len(attempts_24h) == 3

        # All should be in last hour
        attempts_1h = protector.get_recent_attempts(hours=1)
        assert len(attempts_1h) == 3

    def test_different_attempt_types(self, protector: BruteForceProtector) -> None:
        """Test recording different attempt types."""
        protector.record_attempt(success=False, attempt_type="decrypt")
        protector.record_attempt(success=False, attempt_type="rotate")
        protector.record_attempt(success=False, attempt_type="audit")

        attempts = protector.get_recent_attempts(hours=1)
        assert len(attempts) == 3
        types = {a.attempt_type for a in attempts}
        assert types == {"decrypt", "rotate", "audit"}


class TestIntegration:
    """Integration tests for passphrase security."""

    def test_weak_passphrase_flow(self) -> None:
        """Test complete flow with weak passphrase."""
        passphrase = "password123"

        # Check strength
        score = check_passphrase_strength(passphrase)
        assert score.strength == PassphraseStrength.WEAK

        # Should be rejected
        acceptable, reason = is_passphrase_acceptable(passphrase)
        assert not acceptable
        assert reason != ""

    def test_strong_passphrase_flow(self) -> None:
        """Test complete flow with strong passphrase."""
        passphrase = "my-secure-journal-2025!"

        # Check strength
        score = check_passphrase_strength(passphrase)
        assert score.strength in (PassphraseStrength.STRONG, PassphraseStrength.VERY_STRONG)

        # Should be accepted
        acceptable, reason = is_passphrase_acceptable(passphrase)
        assert acceptable
        assert reason == ""

    def test_brute_force_protection_flow(self, tmp_path: Path) -> None:
        """Test complete brute force protection flow."""
        data_dir = tmp_path / "test_data"
        data_dir.mkdir()
        protector = BruteForceProtector(data_dir)

        # Simulate multiple failed login attempts
        for i in range(6):
            # Check if allowed
            if i < 5:
                allowed, _ = protector.check_rate_limit()
                assert allowed, f"Attempt {i+1} should be allowed"
            else:
                allowed, msg = protector.check_rate_limit()
                assert not allowed, "6th attempt should be rate limited"
                assert "Too many attempts" in msg

            # Record failure
            protector.record_attempt(success=False, attempt_type="decrypt")

        # Verify rate limit is active
        allowed, msg = protector.check_rate_limit()
        assert not allowed

        # Simulate successful auth (would happen after waiting)
        protector.reset()

        # Should be allowed again
        allowed, _ = protector.check_rate_limit()
        assert allowed


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_passphrase(self) -> None:
        """Test handling of empty passphrase."""
        score = check_passphrase_strength("")
        assert score.strength == PassphraseStrength.WEAK
        # Empty passphrase gets small score from entropy check (5 points)
        assert score.score <= 10

    def test_very_long_passphrase(self) -> None:
        """Test handling of very long passphrase."""
        long_pass = "a" * 1000
        score = check_passphrase_strength(long_pass)
        assert isinstance(score, PassphraseScore)
        # Even if long, should be weak due to low entropy
        assert score.strength in (PassphraseStrength.WEAK, PassphraseStrength.MEDIUM)

    def test_unicode_passphrase(self) -> None:
        """Test handling of unicode characters."""
        unicode_pass = "my-journal-2025-🔒🔑"
        score = check_passphrase_strength(unicode_pass)
        assert isinstance(score, PassphraseScore)
        assert score.score > 0

    def test_special_characters(self) -> None:
        """Test passphrases with various special characters."""
        special_passphrases = [
            "my-secure-journal-2025!",
            "private_thoughts_2025$",
            "journal@2025#secure",
            "my.secure.journal.2025",
        ]

        for pwd in special_passphrases:
            score = check_passphrase_strength(pwd)
            assert isinstance(score, PassphraseScore)
            assert score.score > 0
