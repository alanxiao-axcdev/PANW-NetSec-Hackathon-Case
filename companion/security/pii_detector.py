"""PII detection for journal entries.

Detects personally identifiable information using regex patterns.
Helps users avoid accidentally storing sensitive data in plaintext.
"""

import logging
import re
from re import Pattern

from companion.models import PIIMatch

logger = logging.getLogger(__name__)

# PII regex patterns
# Note: These are heuristic patterns, not perfect. False positives possible.

# Social Security Number: XXX-XX-XXXX or XXXXXXXXX
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b")

# Email: simplified pattern
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Phone numbers: various formats
# (XXX) XXX-XXXX, XXX-XXX-XXXX, XXX.XXX.XXXX, XXXXXXXXXX
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# Credit card: 13-19 digits with optional spaces/dashes
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{1,7}\b")

# IP Address: IPv4 format
IP_ADDRESS_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# US ZIP code: XXXXX or XXXXX-XXXX
ZIP_CODE_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")


class PIIDetector:
    """Detector for personally identifiable information.

    Scans text for common PII patterns and returns matches with positions
    and confidence scores. Uses regex-based heuristics.

    Example:
        >>> detector = PIIDetector()
        >>> matches = detector.detect("My SSN is 123-45-6789")
        >>> len(matches)
        1
        >>> matches[0].type
        'SSN'
    """

    def __init__(
        self,
        enable_ssn: bool = True,
        enable_email: bool = True,
        enable_phone: bool = True,
        enable_credit_card: bool = True,
        enable_ip: bool = False,  # Less sensitive
        enable_zip: bool = False,  # Less sensitive
    ) -> None:
        """Initialize PII detector.

        Args:
            enable_ssn: Detect Social Security Numbers
            enable_email: Detect email addresses
            enable_phone: Detect phone numbers
            enable_credit_card: Detect credit card numbers
            enable_ip: Detect IP addresses
            enable_zip: Detect ZIP codes
        """
        self.patterns: dict[str, Pattern] = {}

        if enable_ssn:
            self.patterns["SSN"] = SSN_PATTERN
        if enable_email:
            self.patterns["EMAIL"] = EMAIL_PATTERN
        if enable_phone:
            self.patterns["PHONE"] = PHONE_PATTERN
        if enable_credit_card:
            self.patterns["CREDIT_CARD"] = CREDIT_CARD_PATTERN
        if enable_ip:
            self.patterns["IP_ADDRESS"] = IP_ADDRESS_PATTERN
        if enable_zip:
            self.patterns["ZIP_CODE"] = ZIP_CODE_PATTERN

    def detect(self, text: str) -> list[PIIMatch]:
        """Detect PII in text.

        Scans text with all enabled patterns and returns matches.

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIMatch objects for detected PII

        Example:
            >>> detector = PIIDetector()
            >>> matches = detector.detect("Email me at user@example.com")
            >>> matches[0].type
            'EMAIL'
        """
        matches: list[PIIMatch] = []

        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # Calculate confidence based on pattern specificity
                confidence = self._calculate_confidence(pii_type, match.group())

                matches.append(
                    PIIMatch(
                        type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                    )
                )

        # Sort by position in text
        matches.sort(key=lambda m: m.start)

        logger.debug("Detected %d PII matches in text", len(matches))

        return matches

    def _calculate_confidence(self, pii_type: str, value: str) -> float:
        """Calculate confidence score for PII match.

        Uses heuristics to estimate likelihood of true positive.

        Args:
            pii_type: Type of PII detected
            value: Detected value

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with base confidence by type
        confidence = 0.7  # Default

        if pii_type == "SSN":
            # SSN with dashes is more likely to be real
            confidence = 0.9 if "-" in value else 0.6  # Could be any 9-digit number

        elif pii_type == "EMAIL":
            # Check for common domains (higher confidence)
            common_domains = [
                "gmail.com",
                "yahoo.com",
                "outlook.com",
                "hotmail.com",
                "icloud.com",
            ]
            confidence = 0.9 if any(domain in value.lower() for domain in common_domains) else 0.7

        elif pii_type == "PHONE":
            # Format with area code separator increases confidence
            confidence = 0.8 if "(" in value or "-" in value else 0.6

        elif pii_type == "CREDIT_CARD":
            # Use Luhn algorithm check for higher confidence
            confidence = 0.9 if self._luhn_check(value.replace(" ", "").replace("-", "")) else 0.5

        elif pii_type == "IP_ADDRESS":
            # Validate IP octets are in valid range
            confidence = 0.8 if self._valid_ip(value) else 0.3  # Likely false positive

        elif pii_type == "ZIP_CODE":
            # ZIP with extension is more specific
            confidence = 0.8 if "-" in value else 0.5  # Could be any 5-digit number

        return confidence

    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm.

        Args:
            card_number: Credit card number (digits only)

        Returns:
            True if passes Luhn check
        """
        if not card_number.isdigit():
            return False

        # Luhn algorithm
        total = 0
        reverse_digits = card_number[::-1]

        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n

        return total % 10 == 0

    def _valid_ip(self, ip: str) -> bool:
        """Validate IPv4 address.

        Args:
            ip: IP address string

        Returns:
            True if valid IPv4 format
        """
        try:
            octets = [int(x) for x in ip.split(".")]
            return len(octets) == 4 and all(0 <= x <= 255 for x in octets)
        except (ValueError, AttributeError):
            return False


def detect_pii(
    text: str,
    detector: PIIDetector | None = None,
) -> list[PIIMatch]:
    """Convenience function to detect PII in text.

    Args:
        text: Text to scan for PII
        detector: Optional detector instance (creates default if None)

    Returns:
        List of PIIMatch objects

    Example:
        >>> matches = detect_pii("Call me at 555-123-4567")
        >>> matches[0].type
        'PHONE'
    """
    if detector is None:
        detector = PIIDetector()

    return detector.detect(text)


def classify_pii_type(value: str) -> str:  # noqa: PLR0911
    """Classify a value as a specific PII type.

    Attempts to identify what type of PII a given value represents.

    Args:
        value: Value to classify

    Returns:
        PII type string (SSN, EMAIL, PHONE, etc.) or "UNKNOWN"

    Example:
        >>> classify_pii_type("user@example.com")
        'EMAIL'
        >>> classify_pii_type("123-45-6789")
        'SSN'
    """
    # Try each pattern
    if SSN_PATTERN.fullmatch(value):
        return "SSN"
    if EMAIL_PATTERN.fullmatch(value):
        return "EMAIL"
    if PHONE_PATTERN.fullmatch(value):
        return "PHONE"
    if CREDIT_CARD_PATTERN.fullmatch(value):
        return "CREDIT_CARD"
    if IP_ADDRESS_PATTERN.fullmatch(value):
        return "IP_ADDRESS"
    if ZIP_CODE_PATTERN.fullmatch(value):
        return "ZIP_CODE"

    return "UNKNOWN"
