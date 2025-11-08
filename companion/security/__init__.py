"""Security infrastructure for Companion.

Provides encryption, sandboxing, audit logging, and PII detection.
"""

from companion.security.audit import (
    SecurityAuditLog,
    generate_audit_report,
    log_data_access,
    log_model_inference,
    log_security_event,
)
from companion.security.encryption import decrypt_entry, derive_key, encrypt_entry
from companion.security.pii_detector import PIIDetector, classify_pii_type, detect_pii
from companion.security.sandboxing import limit_resources, run_sandboxed, validate_output

__all__ = [
    "PIIDetector",
    "SecurityAuditLog",
    "classify_pii_type",
    "decrypt_entry",
    "derive_key",
    "detect_pii",
    "encrypt_entry",
    "generate_audit_report",
    "limit_resources",
    "log_data_access",
    "log_model_inference",
    "log_security_event",
    "run_sandboxed",
    "validate_output",
]
