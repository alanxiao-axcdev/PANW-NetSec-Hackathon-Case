"""Process isolation and resource limiting for model inference.

Provides sandboxed execution of AI model inference with resource constraints
to prevent resource exhaustion and limit potential security risks.
"""

import logging
import multiprocessing as mp
import signal
import sys
from collections.abc import Callable
from typing import Any

import psutil

# resource module is Unix-only, not available on Windows
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

logger = logging.getLogger(__name__)

# Default resource limits
DEFAULT_MAX_MEMORY_MB = 4096  # 4GB
DEFAULT_MAX_CPU_SECONDS = 300  # 5 minutes
DEFAULT_TIMEOUT_SECONDS = 60  # 1 minute


class ResourceLimitError(Exception):
    """Raised when resource limits are exceeded."""


class ValidationError(Exception):
    """Raised when output validation fails."""


def limit_resources(
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
    max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
) -> None:
    """Set resource limits for the current process.

    Should be called at the start of a subprocess to enforce limits.
    Uses Unix resource limits (RLIMIT_AS for memory, RLIMIT_CPU for CPU time).

    Args:
        max_memory_mb: Maximum memory in megabytes (default: 4096)
        max_cpu_seconds: Maximum CPU time in seconds (default: 300)

    Raises:
        OSError: If setting resource limits fails (e.g., on Windows)

    Example:
        >>> def worker():
        ...     limit_resources(max_memory_mb=1024, max_cpu_seconds=60)
        ...     # Do work within limits
    """
    if not HAS_RESOURCE:
        logger.warning("Resource limits not available on this platform (Windows)")
        return

    try:
        # Set memory limit (address space)
        max_memory_bytes = max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        logger.debug("Set memory limit: %d MB", max_memory_mb)

        # Set CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))
        logger.debug("Set CPU time limit: %d seconds", max_cpu_seconds)

    except (OSError, ValueError) as e:
        logger.warning("Failed to set resource limits: %s", e)
        # Don't fail - some systems (Windows) don't support resource limits


def _worker_wrapper(
    func: Callable,
    args: tuple,
    kwargs: dict,
    result_queue: mp.Queue,
    max_memory_mb: int,
    max_cpu_seconds: int,
) -> None:
    """Worker process wrapper that applies resource limits.

    Args:
        func: Function to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        result_queue: Queue to send result or exception
        max_memory_mb: Memory limit in MB
        max_cpu_seconds: CPU time limit in seconds
    """
    # Apply resource limits in subprocess
    limit_resources(max_memory_mb, max_cpu_seconds)

    try:
        result = func(*args, **kwargs)
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", e))


def run_sandboxed(
    func: Callable,
    *args: Any,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
    max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
    **kwargs: Any,
) -> Any:
    """Run function in isolated subprocess with resource limits.

    Executes the function in a separate process with enforced resource constraints.
    The subprocess is terminated if it exceeds the timeout.

    Args:
        func: Function to execute (must be picklable)
        *args: Positional arguments for func
        timeout: Wall-clock timeout in seconds (default: 60)
        max_memory_mb: Memory limit in MB (default: 4096)
        max_cpu_seconds: CPU time limit in seconds (default: 300)
        **kwargs: Keyword arguments for func

    Returns:
        Result from func execution

    Raises:
        TimeoutError: If execution exceeds timeout
        ResourceLimitError: If resource limits are exceeded
        Exception: Any exception raised by func

    Example:
        >>> def slow_computation(x):
        ...     return x * 2
        >>> result = run_sandboxed(slow_computation, 21, timeout=10)
        >>> result
        42
    """
    # Create queue for result communication
    result_queue = mp.Queue()

    # Start worker process
    process = mp.Process(
        target=_worker_wrapper,
        args=(func, args, kwargs, result_queue, max_memory_mb, max_cpu_seconds),
    )

    logger.debug(
        "Starting sandboxed execution: timeout=%ds, memory=%dMB, cpu=%ds",
        timeout,
        max_memory_mb,
        max_cpu_seconds,
    )

    process.start()

    try:
        # Wait for completion with timeout
        process.join(timeout=timeout)

        if process.is_alive():
            # Timeout exceeded - kill process
            logger.warning("Process exceeded timeout (%ds), terminating", timeout)
            process.terminate()
            process.join(timeout=5)

            if process.is_alive():
                # Force kill if still alive
                process.kill()
                process.join()

            msg = f"Execution exceeded timeout of {timeout} seconds"
            raise TimeoutError(msg)

        # Check exit code
        if process.exitcode != 0:
            # Process crashed or was killed
            # SIGXCPU and SIGKILL are Unix-only signals
            if HAS_RESOURCE and hasattr(signal, 'SIGXCPU') and process.exitcode == -signal.SIGXCPU:
                msg = f"CPU time limit exceeded ({max_cpu_seconds}s)"
                raise ResourceLimitError(msg)
            if hasattr(signal, 'SIGKILL') and process.exitcode == -signal.SIGKILL:
                msg = "Process was killed (likely memory limit exceeded)"
                raise ResourceLimitError(msg)
            msg = f"Process exited with code {process.exitcode}"
            raise RuntimeError(msg)

        # Get result from queue
        if result_queue.empty():
            msg = "No result received from subprocess"
            raise RuntimeError(msg)

        status, value = result_queue.get(timeout=1)

        if status == "error":
            # Re-raise exception from subprocess
            raise value

        return value

    finally:
        # Clean up
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()


def validate_output(output: str, max_length: int = 10000) -> tuple[bool, str]:
    """Validate model output for safety and correctness.

    Checks output for suspicious patterns, excessive length, or invalid content.

    Args:
        output: Model-generated output to validate
        max_length: Maximum allowed length (default: 10000 chars)

    Returns:
        Tuple of (is_valid, reason). If valid, reason is empty string.

    Example:
        >>> valid, reason = validate_output("This is a safe output")
        >>> valid
        True
        >>> valid, reason = validate_output("x" * 20000)
        >>> valid
        False
    """
    if not isinstance(output, str):
        return False, f"Output must be string, got {type(output).__name__}"

    if len(output) > max_length:
        return False, f"Output too long ({len(output)} chars, max {max_length})"

    if not output.strip():
        return False, "Output is empty or whitespace only"

    # Check for suspicious patterns
    suspicious_patterns = [
        ("</script>", "Contains script tags"),
        ("<script", "Contains script tags"),
        ("javascript:", "Contains JavaScript protocol"),
        ("data:text/html", "Contains data URI"),
        ("eval(", "Contains eval()"),
    ]

    output_lower = output.lower()
    for pattern, reason in suspicious_patterns:
        if pattern in output_lower:
            return False, f"Suspicious content: {reason}"

    # Check for excessive repetition (possible model failure)
    if len(output) > 100:
        # Check if output is mostly repetitive
        unique_chars = len(set(output))
        if unique_chars < 10:
            return False, "Output is excessively repetitive"

    return True, ""


def get_process_stats() -> dict[str, Any]:
    """Get current process resource usage statistics.

    Returns:
        Dictionary with memory_mb, cpu_percent, and num_threads

    Example:
        >>> stats = get_process_stats()
        >>> 'memory_mb' in stats
        True
    """
    process = psutil.Process()

    return {
        "memory_mb": process.memory_info().rss / (1024 * 1024),
        "cpu_percent": process.cpu_percent(interval=0.1),
        "num_threads": process.num_threads(),
    }
