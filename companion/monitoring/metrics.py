"""Performance metrics collection and analysis."""

import logging
import statistics
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# In-memory metrics store
_metrics: dict[str, list[float]] = defaultdict(list)
MAX_SAMPLES = 1000  # Keep last 1000 samples per metric


def record_inference_time(duration_ms: float) -> None:
    """Record model inference duration.

    Args:
        duration_ms: Inference time in milliseconds

    Example:
        >>> record_inference_time(150.5)
    """
    _metrics["inference_time_ms"].append(duration_ms)
    _prune_samples("inference_time_ms")
    logger.debug("Recorded inference time: %.2fms", duration_ms)


def record_memory_usage(mb: float) -> None:
    """Record memory usage.

    Args:
        mb: Memory usage in megabytes

    Example:
        >>> record_memory_usage(512.0)
    """
    _metrics["memory_mb"].append(mb)
    _prune_samples("memory_mb")


def record_disk_io(bytes_written: int) -> None:
    """Record disk I/O operations.

    Args:
        bytes_written: Number of bytes written to disk
    """
    _metrics["disk_io_bytes"].append(float(bytes_written))
    _prune_samples("disk_io_bytes")


def get_percentiles(metric: str) -> dict[str, float]:
    """Calculate percentiles for a metric.

    Args:
        metric: Metric name (e.g., "inference_time_ms")

    Returns:
        Dictionary with p50, p95, p99 percentiles

    Example:
        >>> record_inference_time(100.0)
        >>> record_inference_time(200.0)
        >>> percentiles = get_percentiles("inference_time_ms")
        >>> 'p50' in percentiles
        True
    """
    if metric not in _metrics or not _metrics[metric]:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}

    values = sorted(_metrics[metric])
    count = len(values)

    return {
        "p50": _percentile(values, 50),
        "p95": _percentile(values, 95),
        "p99": _percentile(values, 99),
        "count": count,
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
    }


def get_all_metrics() -> dict[str, dict[str, float]]:
    """Get all collected metrics with percentiles.

    Returns:
        Dictionary mapping metric names to their statistics
    """
    return {metric: get_percentiles(metric) for metric in _metrics}


def reset_metrics(metric: str | None = None) -> None:
    """Reset metrics data.

    Args:
        metric: Specific metric to reset, or None to reset all
    """
    if metric:
        _metrics[metric].clear()
    else:
        _metrics.clear()


def _percentile(sorted_values: list[float], p: float) -> float:
    """Calculate percentile from sorted values.

    Args:
        sorted_values: List of values in sorted order
        p: Percentile (0-100)

    Returns:
        Percentile value
    """
    if not sorted_values:
        return 0.0

    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1

    if c >= len(sorted_values):
        return sorted_values[-1]

    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def _prune_samples(metric: str) -> None:
    """Keep only recent samples to limit memory usage.

    Args:
        metric: Metric name to prune
    """
    if len(_metrics[metric]) > MAX_SAMPLES:
        _metrics[metric] = _metrics[metric][-MAX_SAMPLES:]


def get_summary() -> dict[str, Any]:
    """Get summary of all metrics.

    Returns:
        Summary dictionary with key statistics
    """
    summary = {}

    for metric_name in _metrics:
        stats = get_percentiles(metric_name)
        summary[metric_name] = {
            "count": stats["count"],
            "mean": round(stats["mean"], 2),
            "p50": round(stats["p50"], 2),
            "p95": round(stats["p95"], 2),
            "p99": round(stats["p99"], 2),
        }

    return summary
