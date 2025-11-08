"""Circuit breaker pattern for fault tolerance.

Implements the circuit breaker pattern to prevent cascading failures when
external services (like AI models) are experiencing issues.
"""

import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker state.

    Attributes:
        CLOSED: Normal operation, requests pass through
        OPEN: Too many failures, requests blocked
        HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and blocking requests."""



class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    The circuit breaker monitors failures and automatically "opens" to prevent
    further requests when a failure threshold is exceeded. After a timeout,
    it moves to "half-open" to test if the service has recovered.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> result = breaker.call(risky_operation, arg1, arg2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_attempts: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit (default: 5)
            timeout: Seconds to wait before attempting recovery (default: 60)
            half_open_attempts: Successful attempts needed to close circuit (default: 1)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

        logger.info(
            "Circuit breaker initialized: threshold=%d, timeout=%ds",
            failure_threshold,
            timeout,
        )

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result from function execution

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by the function
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info("Circuit breaker timeout elapsed, moving to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                msg = "Circuit breaker is OPEN, request blocked"
                logger.warning(msg)
                raise CircuitBreakerError(msg)

        try:
            # Execute the function
            result = func(*args, **kwargs)
            self.record_success()
            return result

        except Exception:
            self.record_failure()
            raise

    def record_success(self) -> None:
        """Record successful call.

        In HALF_OPEN state, accumulates successful attempts. Once enough
        successes are recorded, transitions to CLOSED state.
        """
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug("HALF_OPEN success count: %d/%d", self.success_count, self.half_open_attempts)

            if self.success_count >= self.half_open_attempts:
                logger.info("Circuit breaker recovered, moving to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug("Resetting failure count after success")
                self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed call, open circuit if threshold exceeded.

        Increments failure count and transitions to OPEN state if the
        failure threshold is reached.
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            "Circuit breaker failure count: %d/%d",
            self.failure_count,
            self.failure_threshold,
        )

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("HALF_OPEN state failed, reopening circuit")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.failure_threshold:
            logger.error("Failure threshold exceeded, opening circuit breaker")
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Useful for administrative intervention or testing.
        """
        logger.info("Circuit breaker manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
