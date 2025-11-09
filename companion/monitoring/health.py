"""Health check system for Companion."""

import logging
import shutil
from pathlib import Path

from companion.models import HealthStatus

logger = logging.getLogger(__name__)


def check_model_loaded() -> HealthStatus:
    """Check if AI model is loaded and responsive.

    Returns:
        HealthStatus with AI model status
    """
    from companion import ai_engine

    if not ai_engine.is_initialized():
        return HealthStatus(
            component="ai_model",
            status="DEGRADED",
            message="AI model not initialized (run: companion health --ai)"
        )

    health_info = ai_engine.get_provider_health()

    if health_info["initialized"] and health_info["model_loaded"]:
        provider = health_info["provider_name"]
        return HealthStatus(
            component="ai_model",
            status="OK",
            message=f"{provider} loaded and ready"
        )

    return HealthStatus(
        component="ai_model",
        status="DOWN",
        message=f"Provider {health_info['provider_name']} failed to load"
    )


def check_storage_accessible(data_dir: Path) -> HealthStatus:
    """Check if storage directory is accessible.

    Args:
        data_dir: Path to data directory

    Returns:
        HealthStatus indicating storage accessibility
    """
    try:
        if not data_dir.exists():
            return HealthStatus(
                component="storage",
                status="DOWN",
                message=f"Data directory does not exist: {data_dir}"
            )

        # Try to write test file
        test_file = data_dir / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()

        return HealthStatus(
            component="storage",
            status="OK",
            message=f"Storage accessible at {data_dir}"
        )
    except (OSError, PermissionError) as e:
        return HealthStatus(
            component="storage",
            status="DOWN",
            message=f"Storage error: {e}"
        )


def check_disk_space(data_dir: Path, min_gb: float = 5.0) -> HealthStatus:
    """Check available disk space.

    Args:
        data_dir: Path to check disk space for
        min_gb: Minimum required GB

    Returns:
        HealthStatus indicating disk space status
    """
    try:
        usage = shutil.disk_usage(data_dir)
        free_gb = usage.free / (1024**3)

        if free_gb < min_gb:
            return HealthStatus(
                component="disk_space",
                status="DEGRADED",
                message=f"Low disk space: {free_gb:.1f}GB free (minimum {min_gb}GB)"
            )

        return HealthStatus(
            component="disk_space",
            status="OK",
            message=f"{free_gb:.1f}GB free"
        )
    except OSError as e:
        return HealthStatus(
            component="disk_space",
            status="DOWN",
            message=f"Cannot check disk space: {e}"
        )


def check_memory_available(min_gb: float = 2.0) -> HealthStatus:
    """Check available system memory.

    Args:
        min_gb: Minimum required GB of available memory

    Returns:
        HealthStatus indicating memory status
    """
    try:
        import psutil

        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)

        if available_gb < min_gb:
            return HealthStatus(
                component="memory",
                status="DEGRADED",
                message=f"Low memory: {available_gb:.1f}GB available (minimum {min_gb}GB)"
            )

        return HealthStatus(
            component="memory",
            status="OK",
            message=f"{available_gb:.1f}GB available"
        )
    except ImportError:
        # psutil not available, return degraded status
        return HealthStatus(
            component="memory",
            status="DEGRADED",
            message="Cannot check memory (psutil not installed)"
        )
    except Exception as e:
        return HealthStatus(
            component="memory",
            status="DOWN",
            message=f"Cannot check memory: {e}"
        )


def run_all_checks(data_dir: Path) -> dict[str, HealthStatus]:
    """Run all health checks.

    Args:
        data_dir: Data directory to check

    Returns:
        Dict mapping component name to HealthStatus
    """
    return {
        "model": check_model_loaded(),
        "storage": check_storage_accessible(data_dir),
        "disk_space": check_disk_space(data_dir),
    }
