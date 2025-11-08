"""Tests for PII detection."""

from companion.security.pii_detector import (
    PIIDetector,
    classify_pii_type,
    detect_pii,
)


class TestPIIDetector:
    """Test PII detection functionality."""

    def test_detect_ssn(self):
        """Should detect Social Security Numbers."""
        detector = PIIDetector()
        text = "My SSN is 123-45-6789"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].type == "SSN"
        assert matches[0].value == "123-45-6789"
        assert matches[0].start == 10  # "My SSN is " = 10 chars
        assert matches[0].confidence > 0.5

    def test_detect_ssn_no_dashes(self):
        """Should detect SSN without dashes."""
        detector = PIIDetector()
        matches = detector.detect("SSN: 123456789")

        assert len(matches) == 1
        assert matches[0].type == "SSN"
        assert matches[0].value == "123456789"

    def test_detect_email(self):
        """Should detect email addresses."""
        detector = PIIDetector()
        text = "Contact me at user@example.com"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].type == "EMAIL"
        assert matches[0].value == "user@example.com"

    def test_detect_phone(self):
        """Should detect phone numbers."""
        detector = PIIDetector()

        test_cases = [
            "(555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "5551234567",
        ]

        for phone in test_cases:
            matches = detector.detect(f"Call me at {phone}")
            assert len(matches) >= 1, f"Failed to detect {phone}"
            assert matches[0].type == "PHONE"

    def test_detect_credit_card(self):
        """Should detect credit card numbers."""
        detector = PIIDetector()
        text = "Card: 4532-1234-5678-9010"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].type == "CREDIT_CARD"

    def test_detect_ip_address(self):
        """Should detect IP addresses when enabled."""
        detector = PIIDetector(enable_ip=True)
        text = "Server IP: 192.168.1.1"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].type == "IP_ADDRESS"
        assert matches[0].value == "192.168.1.1"

    def test_detect_zip_code(self):
        """Should detect ZIP codes when enabled."""
        detector = PIIDetector(enable_zip=True)

        # Standard ZIP
        matches = detector.detect("ZIP: 12345")
        assert len(matches) == 1
        assert matches[0].type == "ZIP_CODE"

        # ZIP+4
        matches = detector.detect("ZIP: 12345-6789")
        assert len(matches) == 1
        assert matches[0].confidence > 0.5

    def test_detect_multiple_pii(self):
        """Should detect multiple PII instances."""
        detector = PIIDetector()
        text = "Email: user@example.com, Phone: 555-123-4567, SSN: 123-45-6789"

        matches = detector.detect(text)

        assert len(matches) == 3
        types = {m.type for m in matches}
        assert types == {"EMAIL", "PHONE", "SSN"}

    def test_detect_no_pii(self):
        """Should return empty list for text without PII."""
        detector = PIIDetector()
        text = "This is a normal sentence with no sensitive data."

        matches = detector.detect(text)

        assert len(matches) == 0

    def test_disabled_patterns(self):
        """Should respect disabled pattern flags."""
        detector = PIIDetector(enable_email=False)
        text = "Email: user@example.com"

        matches = detector.detect(text)

        assert len(matches) == 0

    def test_confidence_scores(self):
        """Should provide confidence scores."""
        detector = PIIDetector()

        # SSN with dashes should have higher confidence
        matches_with_dash = detector.detect("123-45-6789")
        matches_no_dash = detector.detect("123456789")

        assert matches_with_dash[0].confidence > matches_no_dash[0].confidence

    def test_match_positions(self):
        """Should provide accurate text positions."""
        detector = PIIDetector()
        text = "Before 555-123-4567 after"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert text[matches[0].start : matches[0].end] == matches[0].value


class TestLuhnCheck:
    """Test Luhn algorithm for credit cards."""

    def test_valid_credit_card(self):
        """Should validate correct credit card numbers."""
        detector = PIIDetector()

        # Valid Visa test number
        valid_card = "4532015112830366"
        matches = detector.detect(valid_card)

        assert len(matches) == 1
        assert matches[0].confidence > 0.8

    def test_invalid_credit_card(self):
        """Should have lower confidence for invalid cards."""
        detector = PIIDetector()

        # Invalid (fails Luhn check)
        invalid_card = "4532015112830367"
        matches = detector.detect(invalid_card)

        if len(matches) > 0:
            assert matches[0].confidence < 0.9


class TestIPValidation:
    """Test IP address validation."""

    def test_valid_ip(self):
        """Should validate correct IP addresses."""
        detector = PIIDetector(enable_ip=True)

        valid_ips = ["192.168.1.1", "10.0.0.1", "255.255.255.255"]

        for ip in valid_ips:
            matches = detector.detect(ip)
            assert len(matches) == 1, f"Failed to detect {ip}"

    def test_invalid_ip_octets(self):
        """Should have lower confidence for invalid IP octets."""
        detector = PIIDetector(enable_ip=True)

        # Invalid (octets > 255)
        invalid_ip = "999.999.999.999"
        matches = detector.detect(invalid_ip)

        # Might still match pattern but should have low confidence
        if len(matches) > 0:
            assert matches[0].confidence < 0.5


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_pii_function(self):
        """Should work with convenience function."""
        matches = detect_pii("Email: user@example.com")

        assert len(matches) == 1
        assert matches[0].type == "EMAIL"

    def test_classify_pii_type(self):
        """Should classify PII types."""
        assert classify_pii_type("user@example.com") == "EMAIL"
        assert classify_pii_type("123-45-6789") == "SSN"
        assert classify_pii_type("555-123-4567") == "PHONE"
        assert classify_pii_type("12345") == "ZIP_CODE"
        assert classify_pii_type("192.168.1.1") == "IP_ADDRESS"

    def test_classify_unknown(self):
        """Should return UNKNOWN for unrecognized patterns."""
        assert classify_pii_type("random text") == "UNKNOWN"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text(self):
        """Should handle empty text."""
        detector = PIIDetector()
        matches = detector.detect("")
        assert len(matches) == 0

    def test_unicode_text(self):
        """Should handle Unicode text."""
        detector = PIIDetector()
        text = "Email: 用户@example.com 世界"
        detector.detect(text)
        # Should handle Unicode without errors

    def test_very_long_text(self):
        """Should handle long text efficiently."""
        detector = PIIDetector()
        text = "Normal text. " * 1000 + " Email: user@example.com"

        matches = detector.detect(text)

        assert len(matches) == 1
        assert matches[0].type == "EMAIL"

    def test_multiple_same_type(self):
        """Should detect multiple instances of same PII type."""
        detector = PIIDetector()
        text = "Emails: alice@example.com and bob@example.com"

        matches = detector.detect(text)

        assert len(matches) == 2
        assert all(m.type == "EMAIL" for m in matches)

    def test_overlapping_patterns(self):
        """Should handle overlapping or adjacent patterns."""
        detector = PIIDetector()
        text = "123-45-6789 123-45-6788"  # Two SSNs with space

        matches = detector.detect(text)

        # Should detect both when separated
        assert len(matches) >= 1


class TestCommonDomains:
    """Test confidence based on common domains."""

    def test_common_domain_high_confidence(self):
        """Should have higher confidence for common domains."""
        detector = PIIDetector()

        common = detector.detect("user@gmail.com")
        uncommon = detector.detect("user@obscure-site.xyz")

        assert common[0].confidence > uncommon[0].confidence

    def test_various_common_domains(self):
        """Should recognize multiple common domains."""
        detector = PIIDetector()

        domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]

        for domain in domains:
            matches = detector.detect(f"user@{domain}")
            assert len(matches) == 1
            assert matches[0].confidence > 0.8


class TestPhoneFormats:
    """Test various phone number formats."""

    def test_phone_with_country_code(self):
        """Should detect phone with +1 country code."""
        detector = PIIDetector()
        matches = detector.detect("+1-555-123-4567")
        assert len(matches) >= 1

    def test_phone_confidence_by_format(self):
        """Should have higher confidence for formatted numbers."""
        detector = PIIDetector()

        formatted = detector.detect("(555) 123-4567")
        unformatted = detector.detect("5551234567")

        assert formatted[0].confidence >= unformatted[0].confidence
