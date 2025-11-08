"""Monitoring and observability for Companion.

Provides metrics collection, health checks, telemetry, and dashboard display.
"""

from companion.monitoring.dashboard import display_health_status, display_metrics_dashboard
from companion.monitoring.health import (
    HealthStatus,
    check_disk_space,
    check_model_loaded,
    check_storage_accessible,
    run_all_checks,
)
from companion.monitoring.metrics import (
    get_percentiles,
    record_inference_time,
    record_memory_usage,
)
from companion.monitoring.telemetry import get_usage_stats, record_event

__all__ = [
    "HealthStatus",
    "check_disk_space",
    "check_model_loaded",
    "check_storage_accessible",
    "display_health_status",
    "display_metrics_dashboard",
    "get_percentiles",
    "get_usage_stats",
    "record_event",
    "record_inference_time",
    "record_memory_usage",
    "run_all_checks",
]
