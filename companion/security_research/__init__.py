"""AI Security Research modules for Companion.

This package contains novel security research implementations:
- Prompt injection detection with 50+ patterns
- Advanced PII sanitization with multiple obfuscation methods
- Data poisoning detection with baseline profiling
- Adversarial testing framework

These modules demonstrate AI security expertise for PANW NetSec interview.
"""

from companion.security_research.prompt_injection_detector import (
    InjectionType,
    detect_injection,
    classify_injection_type,
    sanitize_for_prompt_context,
    evaluate_prompt_template_robustness,
)

__all__ = [
    "InjectionType",
    "detect_injection",
    "classify_injection_type",
    "sanitize_for_prompt_context",
    "evaluate_prompt_template_robustness",
]
