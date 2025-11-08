"""Utility modules for Companion.

Provides retry logic, circuit breaker, and error classification utilities.
"""

from companion.utils.circuit_breaker import CircuitBreaker, CircuitState
from companion.utils.error_classifier import ErrorClass, classify_error, get_user_message
from companion.utils.retry import retry_with_backoff

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "ErrorClass",
    "classify_error",
    "get_user_message",
    "retry_with_backoff",
]
