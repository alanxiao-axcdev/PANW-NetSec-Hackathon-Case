"""Tests for advanced PII sanitization module.

Tests detection accuracy, all 4 obfuscation methods, and PII analysis.
Target metrics: 91.9% F1 score on labeled dataset.
"""

import json
from pathlib import Path

import pytest

from companion.security_research.pii_sanitizer import (
    ObfuscationMethod,
    analyze_pii_exposure,
    create_sanitized_export,
    detect_pii,
    detokenize_pii,
    obfuscate_pii,
)


@pytest.fixture
def test_cases():
    """Load PII test cases from JSON file."""
    test_file = Path(__file__).parent / "data" / "pii_test_cases.json"
    with open(test_file) as f:
        return json.load(f)


def test_detect_pii_basic(test_cases):
    """Test basic PII detection on labeled cases."""
    for case in test_cases:
        matches = detect_pii(case["text"])
        expected = case["expected"]

        # Check count
        assert len(matches) == len(
            expected
        ), f"Failed on: {case['description']} - expected {len(expected)}, got {len(matches)}"

        # Check types
        if expected:
            detected_types = {m.type for m in matches}
            expected_types = {e["type"] for e in expected}
            assert (
                detected_types == expected_types
            ), f"Failed on: {case['description']}"


def test_detect_pii_with_context():
    """Test context-aware confidence boosting."""
    # With context keyword
    text1 = "My SSN is 123-45-6789"
    matches1 = detect_pii(text1, include_context=True)
    assert len(matches1) == 1
    assert matches1[0].confidence > 0.8  # Should have high confidence with context

    # Without context keyword
    text2 = "The number 123-45-6789 appeared"
    matches2 = detect_pii(text2, include_context=True)
    assert len(matches2) == 1
    # Confidence may be lower without explicit "SSN" keyword


def test_obfuscate_redact():
    """Test REDACT obfuscation method."""
    text = "My SSN is 123-45-6789 and email is john@example.com"
    obfuscated, pii_map = obfuscate_pii(text, "redact")

    assert "123-45-6789" not in obfuscated
    assert "john@example.com" not in obfuscated
    assert "[REDACTED]" in obfuscated
    assert pii_map == {}  # Redact doesn't use map


def test_obfuscate_mask():
    """Test MASK obfuscation method."""
    text = "My SSN is 123-45-6789"
    obfuscated, _ = obfuscate_pii(text, "mask")

    # Should show last 4 digits
    assert "6789" in obfuscated
    assert "123-45" not in obfuscated
    assert "***" in obfuscated or "*" in obfuscated


def test_obfuscate_mask_email():
    """Test MASK for email addresses."""
    text = "Email: john@example.com"
    obfuscated, _ = obfuscate_pii(text, "mask")

    # Should show domain
    assert "example.com" in obfuscated
    assert "john" not in obfuscated
    assert "***@" in obfuscated


def test_obfuscate_mask_phone():
    """Test MASK for phone numbers."""
    text = "Call 555-123-4567"
    obfuscated, _ = obfuscate_pii(text, "mask")

    # Should show last 4 digits
    assert "4567" in obfuscated
    assert "555-123" not in obfuscated


def test_obfuscate_generalize():
    """Test GENERALIZE obfuscation method."""
    text = "SSN: 123-45-6789, Email: john@example.com"
    obfuscated, _ = obfuscate_pii(text, "generalize")

    assert "123-45-6789" not in obfuscated
    assert "john@example.com" not in obfuscated
    assert "[ssn]" in obfuscated
    assert "[email]" in obfuscated


def test_obfuscate_tokenize():
    """Test TOKENIZE obfuscation method (reversible)."""
    text = "My SSN is 123-45-6789"
    obfuscated, pii_map = obfuscate_pii(text, "tokenize")

    # Original should be hidden
    assert "123-45-6789" not in obfuscated

    # Token should be present
    assert "[SSN_1]" in obfuscated

    # Map should allow reversal
    assert "[SSN_1]" in pii_map
    assert pii_map["[SSN_1]"] == "123-45-6789"


def test_tokenize_multiple_same_type():
    """Test tokenization with multiple PII of same type."""
    text = "SSN1: 123-45-6789, SSN2: 987-65-4321"
    obfuscated, pii_map = obfuscate_pii(text, "tokenize")

    # Both should have unique tokens
    assert "[SSN_1]" in obfuscated
    assert "[SSN_2]" in obfuscated

    # Map should have both
    assert len(pii_map) == 2
    assert "123-45-6789" in pii_map.values()
    assert "987-65-4321" in pii_map.values()


def test_detokenize_pii():
    """Test reversing tokenization."""
    original = "My SSN is 123-45-6789 and email is john@example.com"
    obfuscated, pii_map = obfuscate_pii(original, "tokenize")

    # Reverse tokenization
    restored = detokenize_pii(obfuscated, pii_map)

    # Should match original
    assert "123-45-6789" in restored
    assert "john@example.com" in restored


def test_create_sanitized_export():
    """Test creating sanitized export of entries."""
    entries = [
        {"content": "My SSN is 123-45-6789"},
        {"content": "Email me at john@example.com"},
        {"content": "Today was a good day"},  # No PII
    ]

    sanitized = create_sanitized_export(entries, "generalize")

    assert len(sanitized) == 3
    assert "123-45-6789" not in sanitized[0]
    assert "[ssn]" in sanitized[0]
    assert "john@example.com" not in sanitized[1]
    assert "[email]" in sanitized[1]
    assert sanitized[2] == "Today was a good day"  # Unchanged


def test_analyze_pii_exposure_high_risk():
    """Test PII exposure analysis with high-risk data."""
    entries = [
        {"content": "My SSN is 123-45-6789"},
        {"content": "Card: 4532-1234-5678-9010"},
    ]

    analysis = analyze_pii_exposure(entries)

    assert analysis["risk_level"] == "HIGH"
    assert "SSN" in analysis["pii_types_found"]
    assert "CREDIT_CARD" in analysis["pii_types_found"]
    assert analysis["total_matches"] >= 2
    assert analysis["entries_with_pii"] == 2


def test_analyze_pii_exposure_medium_risk():
    """Test PII exposure analysis with medium-risk data."""
    entries = [
        {"content": "Email: john@example.com"},
        {"content": "Phone: 555-123-4567"},
    ]

    analysis = analyze_pii_exposure(entries)

    assert analysis["risk_level"] in ["MEDIUM", "HIGH"]
    assert "EMAIL" in analysis["pii_types_found"]
    assert "PHONE" in analysis["pii_types_found"]


def test_analyze_pii_exposure_low_risk():
    """Test PII exposure analysis with no PII."""
    entries = [
        {"content": "Today was a good day"},
        {"content": "I went to the store"},
    ]

    analysis = analyze_pii_exposure(entries)

    assert analysis["risk_level"] == "LOW"
    assert len(analysis["pii_types_found"]) == 0
    assert analysis["total_matches"] == 0
    assert analysis["entries_with_pii"] == 0


def test_obfuscate_with_predetected_matches():
    """Test obfuscation with pre-detected PII matches."""
    text = "My SSN is 123-45-6789"
    matches = detect_pii(text)

    # Pass pre-detected matches
    obfuscated, _ = obfuscate_pii(text, "redact", pii_matches=matches)

    assert "[REDACTED]" in obfuscated
    assert "123-45-6789" not in obfuscated


def test_obfuscate_empty_text():
    """Test obfuscation with empty text."""
    obfuscated, pii_map = obfuscate_pii("", "redact")
    assert obfuscated == ""
    assert pii_map == {}


def test_obfuscate_no_pii():
    """Test obfuscation with text containing no PII."""
    text = "Today was a good day"
    obfuscated, pii_map = obfuscate_pii(text, "redact")

    assert obfuscated == text  # Unchanged
    assert pii_map == {}


def test_all_obfuscation_methods():
    """Test all 4 obfuscation methods on same text."""
    text = "SSN: 123-45-6789, Email: john@example.com"

    methods = ["redact", "mask", "generalize", "tokenize"]
    results = {}

    for method in methods:
        obfuscated, _ = obfuscate_pii(text, method)  # type: ignore
        results[method] = obfuscated

        # All should hide original PII
        assert "123-45-6789" not in obfuscated
        assert "john@example.com" not in obfuscated

    # Each method should produce different output
    assert results["redact"] != results["mask"]
    assert results["mask"] != results["generalize"]
    assert results["generalize"] != results["tokenize"]


def test_mask_different_pii_types():
    """Test masking preserves last digits/domain for different types."""
    test_cases = [
        ("123-45-6789", "SSN", "6789"),  # Last 4 of SSN
        ("555-123-4567", "PHONE", "4567"),  # Last 4 of phone
        ("john@example.com", "EMAIL", "example.com"),  # Domain
        ("4532-1234-5678-9010", "CREDIT_CARD", "9010"),  # Last 4 of card
    ]

    for value, pii_type, expected_visible in test_cases:
        text = f"Value: {value}"
        obfuscated, _ = obfuscate_pii(text, "mask")
        assert expected_visible in obfuscated, f"Failed for {pii_type}"
        assert value not in obfuscated or len(value) <= 4


def test_detection_precision_recall(test_cases):
    """Calculate precision and recall on test dataset."""
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for case in test_cases:
        detected = detect_pii(case["text"])
        expected = case["expected"]

        detected_types = {m.type for m in detected}
        expected_types = {e["type"] for e in expected}

        # True positives: correctly detected
        tp = len(detected_types & expected_types)
        true_positives += tp

        # False positives: detected but not expected
        fp = len(detected_types - expected_types)
        false_positives += fp

        # False negatives: expected but not detected
        fn = len(expected_types - detected_types)
        false_negatives += fn

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    print("\n" + "=" * 60)
    print("PII DETECTION METRICS")
    print("=" * 60)
    print(f"Precision:     {precision:.1%}")
    print(f"Recall:        {recall:.1%}")
    print(f"F1 Score:      {f1_score:.1%}")
    print(f"True Positives:  {true_positives}")
    print(f"False Positives: {false_positives}")
    print(f"False Negatives: {false_negatives}")
    print("=" * 60)

    # Target: 91.9% F1 score
    assert f1_score >= 0.85, f"F1 score too low: {f1_score:.1%} (target: 85%+)"


def test_context_awareness_improves_confidence():
    """Test that context keywords increase confidence."""
    # With explicit keyword
    text_with_context = "My SSN is 123-45-6789"
    matches_with = detect_pii(text_with_context, include_context=True)

    # Without keyword (disable context)
    matches_without = detect_pii(text_with_context, include_context=False)

    assert len(matches_with) == len(matches_without)
    # Context-aware should have higher confidence
    if matches_with and matches_without:
        assert matches_with[0].confidence >= matches_without[0].confidence


def test_analyze_pii_details_by_type():
    """Test that analysis provides per-type statistics."""
    entries = [
        {"content": "SSN: 123-45-6789, Email: john@example.com"},
        {"content": "Another SSN: 987-65-4321"},
    ]

    analysis = analyze_pii_exposure(entries)

    assert "details_by_type" in analysis
    assert analysis["details_by_type"]["SSN"] == 2
    assert analysis["details_by_type"]["EMAIL"] == 1


def test_sanitized_export_preserves_order():
    """Test that sanitized export preserves entry order."""
    entries = [
        {"content": "First entry with SSN: 123-45-6789"},
        {"content": "Second entry"},
        {"content": "Third entry with email: test@test.com"},
    ]

    sanitized = create_sanitized_export(entries)

    assert len(sanitized) == 3
    assert "First" in sanitized[0]
    assert "Second" in sanitized[1]
    assert "Third" in sanitized[2]
