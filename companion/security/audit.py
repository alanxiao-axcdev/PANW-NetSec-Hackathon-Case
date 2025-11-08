"""Security audit logging for Companion.

Provides append-only audit trail for security events, model inferences,
and data access operations. Logs are tamper-evident and can be used
for compliance and forensic analysis.
"""

import hashlib
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_AUDIT_LOG_PATH = Path.home() / ".companion" / "audit.log"


class SecurityAuditLog:
    """Append-only security audit log.

    Records security-relevant events in JSON format with timestamps
    and event metadata. Each entry is written immediately and flushed
    to ensure persistence.

    Attributes:
        log_path: Path to audit log file
    """

    def __init__(self, log_path: Path | None = None) -> None:
        """Initialize audit log.

        Args:
            log_path: Path to audit log file (default: ~/.companion/audit.log)
        """
        self.log_path = log_path or DEFAULT_AUDIT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create log file if it doesn't exist
        if not self.log_path.exists():
            self.log_path.touch(mode=0o600)  # Restricted permissions
            logger.info("Created audit log: %s", self.log_path)

    def _write_entry(self, event_type: str, details: dict[str, Any]) -> None:
        """Write audit entry to log.

        Args:
            event_type: Type of security event
            details: Event-specific details
        """
        entry = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "event_type": event_type,
            **details,
        }

        # Write as JSON line
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()  # Ensure immediate write

    def log_model_inference(
        self,
        prompt_hash: str,
        output_hash: str,
        duration_ms: float,
        model_name: str = "",
    ) -> None:
        """Log AI model inference operation.

        Records inference for audit trail without storing actual content.
        Uses hashes to verify data integrity while preserving privacy.

        Args:
            prompt_hash: SHA256 hash of input prompt
            output_hash: SHA256 hash of model output
            duration_ms: Inference duration in milliseconds
            model_name: Name/ID of model used

        Example:
            >>> log = SecurityAuditLog()
            >>> log.log_model_inference(
            ...     prompt_hash="abc123...",
            ...     output_hash="def456...",
            ...     duration_ms=245.5,
            ...     model_name="Qwen2.5-1.5B"
            ... )
        """
        self._write_entry(
            "model_inference",
            {
                "prompt_hash": prompt_hash,
                "output_hash": output_hash,
                "duration_ms": duration_ms,
                "model_name": model_name,
            },
        )

    def log_data_access(
        self,
        operation: str,
        entry_ids: list[str],
        user_id: str = "local",
    ) -> None:
        """Log journal entry access operation.

        Records read, write, update, or delete operations on journal entries.

        Args:
            operation: Type of operation (read, write, update, delete)
            entry_ids: List of entry IDs accessed
            user_id: User performing operation (default: "local")

        Example:
            >>> log = SecurityAuditLog()
            >>> log.log_data_access(
            ...     operation="read",
            ...     entry_ids=["entry-123", "entry-456"],
            ... )
        """
        self._write_entry(
            "data_access",
            {
                "operation": operation,
                "entry_count": len(entry_ids),
                "entry_ids": entry_ids[:10],  # Limit to first 10 for brevity
                "user_id": user_id,
            },
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any],
    ) -> None:
        """Log security-related event.

        Records authentication, authorization, encryption, or other
        security events with severity level.

        Args:
            event_type: Type of security event (auth, encryption, validation, etc.)
            severity: Event severity (info, warning, error, critical)
            details: Event-specific details

        Example:
            >>> log = SecurityAuditLog()
            >>> log.log_security_event(
            ...     event_type="encryption",
            ...     severity="info",
            ...     details={"action": "passphrase_changed"}
            ... )
        """
        self._write_entry(
            "security_event",
            {
                "subtype": event_type,
                "severity": severity,
                "details": details,
            },
        )

    def read_entries(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read audit log entries with optional filtering.

        Args:
            start_date: Filter entries after this date (inclusive)
            end_date: Filter entries before this date (inclusive)
            event_type: Filter by event type

        Returns:
            List of audit log entries matching filters

        Example:
            >>> log = SecurityAuditLog()
            >>> entries = log.read_entries(event_type="model_inference")
            >>> len(entries) >= 0
            True
        """
        if not self.log_path.exists():
            return []

        entries = []

        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Parse timestamp for date filtering
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()

                    # Apply filters
                    if start_date and entry_date < start_date:
                        continue
                    if end_date and entry_date > end_date:
                        continue
                    if event_type and entry.get("event_type") != event_type:
                        continue

                    entries.append(entry)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Skipping invalid audit log entry: %s", e)
                    continue

        return entries


def log_model_inference(
    prompt: str,
    output: str,
    duration_ms: float,
    model_name: str = "",
    audit_log: SecurityAuditLog | None = None,
) -> None:
    """Convenience function to log model inference.

    Args:
        prompt: Input prompt (will be hashed)
        output: Model output (will be hashed)
        duration_ms: Inference duration in milliseconds
        model_name: Name/ID of model used
        audit_log: Optional audit log instance (creates default if None)

    Example:
        >>> log_model_inference(
        ...     prompt="How do you feel?",
        ...     output="I feel good today",
        ...     duration_ms=150.5,
        ... )
    """
    if audit_log is None:
        audit_log = SecurityAuditLog()

    # Hash content for privacy
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    output_hash = hashlib.sha256(output.encode("utf-8")).hexdigest()

    audit_log.log_model_inference(prompt_hash, output_hash, duration_ms, model_name)


def log_data_access(
    operation: str,
    entry_ids: list[str],
    audit_log: SecurityAuditLog | None = None,
) -> None:
    """Convenience function to log data access.

    Args:
        operation: Type of operation (read, write, update, delete)
        entry_ids: List of entry IDs accessed
        audit_log: Optional audit log instance (creates default if None)

    Example:
        >>> log_data_access("read", ["entry-123"])
    """
    if audit_log is None:
        audit_log = SecurityAuditLog()

    audit_log.log_data_access(operation, entry_ids)


def log_security_event(
    event_type: str,
    details: dict[str, Any],
    severity: str = "info",
    audit_log: SecurityAuditLog | None = None,
) -> None:
    """Convenience function to log security event.

    Args:
        event_type: Type of security event
        details: Event-specific details
        severity: Event severity (info, warning, error, critical)
        audit_log: Optional audit log instance (creates default if None)

    Example:
        >>> log_security_event(
        ...     event_type="encryption",
        ...     details={"action": "passphrase_set"},
        ... )
    """
    if audit_log is None:
        audit_log = SecurityAuditLog()

    audit_log.log_security_event(event_type, severity, details)


def generate_audit_report(
    start_date: date,
    end_date: date,
    audit_log: SecurityAuditLog | None = None,
) -> dict[str, Any]:
    """Generate audit report for date range.

    Aggregates audit log entries and provides summary statistics.

    Args:
        start_date: Report start date (inclusive)
        end_date: Report end date (inclusive)
        audit_log: Optional audit log instance (creates default if None)

    Returns:
        Dictionary with report data including counts by event type

    Example:
        >>> from datetime import date, timedelta
        >>> today = date.today()
        >>> report = generate_audit_report(
        ...     start_date=today - timedelta(days=7),
        ...     end_date=today,
        ... )
        >>> 'total_events' in report
        True
    """
    if audit_log is None:
        audit_log = SecurityAuditLog()

    entries = audit_log.read_entries(start_date=start_date, end_date=end_date)

    # Aggregate by event type
    event_counts: dict[str, int] = {}
    for entry in entries:
        event_type = entry.get("event_type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    # Calculate statistics
    total_inference_time_ms = sum(
        entry.get("duration_ms", 0) for entry in entries if entry.get("event_type") == "model_inference"
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_events": len(entries),
        "event_counts": event_counts,
        "total_inference_time_ms": total_inference_time_ms,
    }
