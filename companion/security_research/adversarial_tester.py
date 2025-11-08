"""Comprehensive security testing framework.

This module provides adversarial testing against:
- OWASP LLM Top 10 (LLM01: Prompt Injection)
- PII detection and sanitization
- Data poisoning attacks
- Integration testing across all security modules

Generates comprehensive security reports with quantitative metrics.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from companion.security_research.data_poisoning_detector import (
    build_user_baseline,
    detect_poisoning_attempt,
)
from companion.security_research.pii_sanitizer import detect_pii, obfuscate_pii
from companion.security_research.prompt_injection_detector import detect_injection

logger = logging.getLogger(__name__)


def run_owasp_llm_tests() -> dict[str, Any]:
    """Test against OWASP Top 10 for LLM Applications.

    Focuses on LLM01: Prompt Injection

    Returns:
        Dict with test results for each category
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "framework": "OWASP LLM Top 10",
        "tests": {},
    }

    # LLM01: Prompt Injection
    injection_results = test_injection_resistance()
    results["tests"]["LLM01_Prompt_Injection"] = injection_results

    # Calculate overall OWASP compliance
    passed_tests = sum(1 for t in results["tests"].values() if t.get("passed", False))
    total_tests = len(results["tests"])
    results["overall_pass_rate"] = (
        passed_tests / total_tests if total_tests > 0 else 0
    )

    return results


def test_injection_resistance(test_cases_file: str | None = None) -> dict[str, Any]:
    """Test prompt injection detection.

    Args:
        test_cases_file: Path to test cases JSON (or None for default)

    Returns:
        Dict with detection metrics
    """
    if test_cases_file is None:
        test_cases_file = str(
            Path(__file__).parent.parent.parent / "tests" / "data" / "injection_test_cases.json"
        )

    try:
        with open(test_cases_file) as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        logger.error(f"Test cases file not found: {test_cases_file}")
        return {"error": "Test cases not found"}

    total_cases = len(test_cases)
    high_risk_cases = [c for c in test_cases if c["expected"] == "HIGH"]
    medium_risk_cases = [c for c in test_cases if c["expected"] == "MEDIUM"]
    low_risk_cases = [c for c in test_cases if c["expected"] == "LOW"]

    detected_high = 0
    detected_medium = 0
    false_positives = 0
    missed_cases = []

    for case in high_risk_cases:
        result = detect_injection(case["input"])
        if result.level == "HIGH":
            detected_high += 1
        else:
            missed_cases.append(
                {"description": case["description"], "expected": "HIGH", "got": result.level}
            )

    for case in medium_risk_cases:
        result = detect_injection(case["input"])
        if result.level in ["MEDIUM", "HIGH"]:
            detected_medium += 1

    for case in low_risk_cases:
        result = detect_injection(case["input"])
        if result.level in ["MEDIUM", "HIGH"]:
            false_positives += 1

    detection_rate = (
        detected_high / len(high_risk_cases) if high_risk_cases else 0
    )
    fp_rate = false_positives / len(low_risk_cases) if low_risk_cases else 0

    return {
        "total_cases": total_cases,
        "high_risk_tested": len(high_risk_cases),
        "high_risk_detected": detected_high,
        "detection_rate": detection_rate,
        "false_positives": false_positives,
        "false_positive_rate": fp_rate,
        "missed_cases": missed_cases[:5],  # Top 5 missed
        "passed": detection_rate >= 0.90 and fp_rate <= 0.10,
    }


def test_pii_detection_accuracy(test_cases_file: str | None = None) -> dict[str, Any]:
    """Test PII detection precision/recall.

    Args:
        test_cases_file: Path to test cases JSON (or None for default)

    Returns:
        Dict with precision, recall, F1 score
    """
    if test_cases_file is None:
        test_cases_file = str(
            Path(__file__).parent.parent.parent / "tests" / "data" / "pii_test_cases.json"
        )

    try:
        with open(test_cases_file) as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        logger.error(f"Test cases file not found: {test_cases_file}")
        return {"error": "Test cases not found"}

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    per_type_accuracy: dict[str, dict[str, int]] = {}

    for case in test_cases:
        detected = detect_pii(case["text"])
        expected = case["expected"]

        detected_types = {m.type for m in detected}
        expected_types = {e["type"] for e in expected}

        # True positives
        tp = len(detected_types & expected_types)
        true_positives += tp

        # False positives
        fp = len(detected_types - expected_types)
        false_positives += fp

        # False negatives
        fn = len(expected_types - detected_types)
        false_negatives += fn

        # Per-type tracking
        for pii_type in detected_types | expected_types:
            if pii_type not in per_type_accuracy:
                per_type_accuracy[pii_type] = {"tp": 0, "fp": 0, "fn": 0}

            if pii_type in detected_types and pii_type in expected_types:
                per_type_accuracy[pii_type]["tp"] += 1
            elif pii_type in detected_types:
                per_type_accuracy[pii_type]["fp"] += 1
            elif pii_type in expected_types:
                per_type_accuracy[pii_type]["fn"] += 1

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

    return {
        "total_cases": len(test_cases),
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "per_type_accuracy": per_type_accuracy,
        "passed": f1_score >= 0.85,
    }


def test_poisoning_detection_sensitivity(
    test_cases_file: str | None = None,
) -> dict[str, Any]:
    """Test data poisoning detection.

    Args:
        test_cases_file: Path to test cases JSON (or None for default)

    Returns:
        Dict with detection and false positive rates
    """
    if test_cases_file is None:
        test_cases_file = str(
            Path(__file__).parent.parent.parent
            / "tests"
            / "data"
            / "poisoning_test_cases.json"
        )

    try:
        with open(test_cases_file) as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        logger.error(f"Test cases file not found: {test_cases_file}")
        return {"error": "Test cases not found"}

    # Create baseline from first clean entries
    from companion.models import JournalEntry, Sentiment

    clean_cases = [c for c in test_cases if not c["is_poisoned"]][:10]
    baseline_entries = [
        JournalEntry(
            id=f"baseline_{i}",
            timestamp=datetime.now(),
            content=c["text"],
            sentiment=Sentiment(label="neutral", confidence=0.8),
            word_count=len(c["text"].split()),
        )
        for i, c in enumerate(clean_cases)
    ]

    baseline = build_user_baseline(baseline_entries)

    poisoned_cases = [c for c in test_cases if c["is_poisoned"]]
    clean_test_cases = [c for c in test_cases if not c["is_poisoned"]][10:]  # Skip baseline

    poisoned_detected = 0
    false_positives = 0

    for case in poisoned_cases:
        entry = JournalEntry(
            id="test",
            timestamp=datetime.now(),
            content=case["text"],
            sentiment=Sentiment(label="neutral", confidence=0.8),
            word_count=len(case["text"].split()),
        )
        risk = detect_poisoning_attempt(entry, baseline)
        if risk.level in ["MEDIUM", "HIGH"]:
            poisoned_detected += 1

    for case in clean_test_cases:
        entry = JournalEntry(
            id="test",
            timestamp=datetime.now(),
            content=case["text"],
            sentiment=Sentiment(label="neutral", confidence=0.8),
            word_count=len(case["text"].split()),
        )
        risk = detect_poisoning_attempt(entry, baseline)
        if risk.level == "HIGH":
            false_positives += 1

    detection_rate = (
        poisoned_detected / len(poisoned_cases) if poisoned_cases else 0
    )
    fp_rate = (
        false_positives / len(clean_test_cases) if clean_test_cases else 0
    )

    return {
        "clean_tested": len(clean_test_cases),
        "poisoned_tested": len(poisoned_cases),
        "detection_rate": detection_rate,
        "false_positive_rate": fp_rate,
        "poisoned_detected": poisoned_detected,
        "false_positives": false_positives,
        "passed": detection_rate >= 0.75 and fp_rate <= 0.15,
    }


def generate_comprehensive_security_report(output_file: str | None = None) -> str:
    """Generate markdown security testing report.

    Runs all test suites and creates formatted report matching
    docs/RESEARCH_FINDINGS.md template.

    Args:
        output_file: Path to save report (or None to return as string)

    Returns:
        Markdown formatted report
    """
    logger.info("Running comprehensive security tests...")

    # Run all test suites
    injection_results = test_injection_resistance()
    pii_results = test_pii_detection_accuracy()
    poisoning_results = test_poisoning_detection_sensitivity()
    owasp_results = run_owasp_llm_tests()

    # Generate report
    report_lines = [
        "# Companion AI Security Testing Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Executive Summary",
        "",
        "This report presents comprehensive security testing results for the Companion AI journaling application's security research modules.",
        "",
        "### Overall Results",
        "",
        f"- **Prompt Injection Detection:** {injection_results['detection_rate']:.1%} detection rate, {injection_results['false_positive_rate']:.1%} false positives",
        f"- **PII Detection:** {pii_results['f1_score']:.1%} F1 score (Precision: {pii_results['precision']:.1%}, Recall: {pii_results['recall']:.1%})",
        f"- **Data Poisoning Detection:** {poisoning_results['detection_rate']:.1%} detection rate, {poisoning_results['false_positive_rate']:.1%} false positives",
        f"- **OWASP LLM Compliance:** {owasp_results['overall_pass_rate']:.1%} pass rate",
        "",
        "---",
        "",
        "## 1. Prompt Injection Detection (OWASP LLM01)",
        "",
        f"**Test Cases:** {injection_results['total_cases']} total",
        f"**High Risk Detection:** {injection_results['high_risk_detected']}/{injection_results['high_risk_tested']} ({injection_results['detection_rate']:.1%})",
        f"**False Positives:** {injection_results['false_positives']} ({injection_results['false_positive_rate']:.1%})",
        f"**Status:** {'✅ PASSED' if injection_results['passed'] else '❌ FAILED'}",
        "",
        "### Detection Patterns",
        "",
        "- 50+ injection patterns from OWASP LLM Top 10 and real-world attacks",
        "- Instruction override detection (ignore/disregard/forget patterns)",
        "- Known jailbreak patterns (DAN, APOPHIS, developer mode)",
        "- System impersonation detection (system/assistant markers)",
        "- Delimiter attack detection",
        "",
        "---",
        "",
        "## 2. PII Detection and Sanitization",
        "",
        f"**Test Cases:** {pii_results['total_cases']} labeled examples",
        f"**Precision:** {pii_results['precision']:.1%}",
        f"**Recall:** {pii_results['recall']:.1%}",
        f"**F1 Score:** {pii_results['f1_score']:.1%}",
        f"**Status:** {'✅ PASSED' if pii_results['passed'] else '❌ FAILED'}",
        "",
        "### PII Types Detected",
        "",
        "| Type | True Positives | False Positives | False Negatives |",
        "|------|----------------|-----------------|-----------------|",
    ]

    # Add per-type accuracy table
    for pii_type, metrics in pii_results["per_type_accuracy"].items():
        report_lines.append(
            f"| {pii_type} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} |"
        )

    report_lines.extend(
        [
            "",
            "### Obfuscation Methods",
            "",
            "- **REDACT:** Complete removal with `[REDACTED]` placeholder",
            "- **MASK:** Partial masking showing last 4 digits/domain",
            "- **GENERALIZE:** Type-based replacement (`[ssn]`, `[email]`)",
            "- **TOKENIZE:** Reversible tokenization for secure storage",
            "",
            "---",
            "",
            "## 3. Data Poisoning Detection",
            "",
            f"**Poisoned Entries Tested:** {poisoning_results['poisoned_tested']}",
            f"**Clean Entries Tested:** {poisoning_results['clean_tested']}",
            f"**Detection Rate:** {poisoning_results['detection_rate']:.1%}",
            f"**False Positive Rate:** {poisoning_results['false_positive_rate']:.1%}",
            f"**Status:** {'✅ PASSED' if poisoning_results['passed'] else '❌ FAILED'}",
            "",
            "### Detection Mechanisms",
            "",
            "- **Baseline Profiling:** User writing style, vocabulary, sentiment patterns",
            "- **Instruction Density Analysis:** Detection of command-like language",
            "- **Semantic Drift:** Embedding-based anomaly detection",
            "- **Cross-Entry Patterns:** Systematic bias injection detection",
            "- **Analysis Consistency:** Validation against hallucinations",
            "",
            "---",
            "",
            "## 4. Novel Contributions",
            "",
            "This research demonstrates novel AI security capabilities:",
            "",
            "1. **Context-Aware PII Detection:** Enhanced confidence scoring using surrounding context",
            "2. **Baseline Profiling for Poisoning:** User-specific writing style anomaly detection",
            "3. **Multi-Method Obfuscation:** Four distinct PII sanitization strategies",
            "4. **Cross-Entry Analysis:** Detection of systematic manipulation attempts",
            "",
            "---",
            "",
            "## 5. Recommendations",
            "",
            "### For Production Deployment",
            "",
            "1. **Enable All Detection Modules:** Prompt injection, PII, and poisoning detection",
            "2. **Build User Baselines:** Collect 10-20 entries before enabling poisoning detection",
            "3. **Configure Obfuscation:** Choose appropriate PII obfuscation method for use case",
            "4. **Monitor Metrics:** Track detection rates and false positives in production",
            "",
            "### Future Research",
            "",
            "1. **Semantic Embedding Integration:** Use embeddings for better semantic drift detection",
            "2. **Adaptive Thresholds:** Machine learning for user-specific detection tuning",
            "3. **Multilingual Support:** Extend patterns to non-English languages",
            "4. **Real-time Monitoring:** Dashboard for security metrics visualization",
            "",
            "---",
            "",
            f"**Report Generated:** {datetime.now().isoformat()}",
            f"**Companion Version:** 1.0.0",
            "",
        ]
    )

    report = "\n".join(report_lines)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        logger.info(f"Report saved to {output_file}")

    return report
