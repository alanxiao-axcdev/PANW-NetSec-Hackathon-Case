"""Retry logic with exponential backoff.

Provides async retry functionality for handling transient failures in
AI model inference and network operations.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """Retry async function with exponential backoff.

    Attempts to execute an async function, retrying on failure with
    exponentially increasing delay between attempts. Useful for handling
    transient errors like network timeouts or temporary API failures.

    Args:
        func: Async function to execute (should be a coroutine)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 10.0)
        exceptions: Tuple of exception types to catch and retry (default: all)

    Returns:
        Result from successful function execution

    Raises:
        The last exception encountered if all retries are exhausted

    Example:
        >>> async def flaky_api_call():
        ...     # Might fail occasionally
        ...     return await fetch_from_api()
        >>> result = await retry_with_backoff(flaky_api_call, max_retries=5)
    """
    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()

            if attempt > 0:
                logger.info("Succeeded after %d retries", attempt)

            return result

        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error("Failed after %d attempts: %s", max_retries + 1, e)
                raise

            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.2fs...",
                attempt + 1,
                max_retries + 1,
                e,
                delay,
            )

            await asyncio.sleep(delay)

            # Exponential backoff: double the delay for next retry
            delay = min(delay * 2, max_delay)

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception

    msg = "Retry logic error: no result and no exception"
    raise RuntimeError(msg)


async def retry_with_timeout(
    func: Callable,
    timeout: float = 30.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Retry async function with both timeout and backoff.

    Combines timeout protection with retry logic. Useful for operations
    that might hang indefinitely.

    Args:
        func: Async function to execute
        timeout: Timeout in seconds for each attempt (default: 30.0)
        max_retries: Maximum retry attempts (default: 3)
        base_delay: Initial delay between retries (default: 1.0)

    Returns:
        Result from successful function execution

    Raises:
        TimeoutError: If operation times out on all attempts
        Exception: Any other exception from the function

    Example:
        >>> async def slow_operation():
        ...     await asyncio.sleep(5)
        ...     return "done"
        >>> result = await retry_with_timeout(slow_operation, timeout=10.0)
    """

    async def wrapped_func():
        return await asyncio.wait_for(func(), timeout=timeout)

    return await retry_with_backoff(
        wrapped_func,
        max_retries=max_retries,
        base_delay=base_delay,
        exceptions=(asyncio.TimeoutError, Exception),
    )
