"""Classify errors for appropriate handling.

Provides error classification and user-friendly error messages to guide
recovery strategies and improve user experience.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorClass(Enum):
    """Error classification for handling strategy.

    Attributes:
        TRANSIENT: Temporary error, retry likely to succeed
        PERMANENT: Persistent error, retry won't help
        DEGRADED: Service available but degraded, use fallback
    """

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    DEGRADED = "degraded"


def classify_error(error: Exception) -> ErrorClass:
    """Classify error type for appropriate handling.

    Analyzes an exception to determine whether it represents a transient
    failure (retry), permanent failure (don't retry), or degraded service
    (use fallback).

    Args:
        error: Exception to classify

    Returns:
        ErrorClass indicating handling strategy

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     if classify_error(e) == ErrorClass.TRANSIENT:
        ...         retry_operation()
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()

    # Network and timeout errors are transient
    transient_indicators = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "503",
        "504",
        "429",  # Rate limit
    ]

    for indicator in transient_indicators:
        if indicator in error_type.lower() or indicator in error_msg:
            logger.debug("Classified error as TRANSIENT: %s", error_type)
            return ErrorClass.TRANSIENT

    # Configuration and validation errors are permanent
    permanent_indicators = [
        "notfound",
        "filenotfound",
        "permission",
        "value",
        "type",
        "attribute",
        "key",
        "validation",
        "400",
        "401",
        "403",
        "404",
    ]

    for indicator in permanent_indicators:
        if indicator in error_type.lower() or indicator in error_msg:
            logger.debug("Classified error as PERMANENT: %s", error_type)
            return ErrorClass.PERMANENT

    # Model loading or inference slowness suggests degraded service
    degraded_indicators = [
        "model",
        "inference",
        "memory",
        "resource",
        "slow",
        "degraded",
        "502",
    ]

    for indicator in degraded_indicators:
        if indicator in error_type.lower() or indicator in error_msg:
            logger.debug("Classified error as DEGRADED: %s", error_type)
            return ErrorClass.DEGRADED

    # Default to transient for unknown errors
    logger.debug("Classified unknown error as TRANSIENT: %s", error_type)
    return ErrorClass.TRANSIENT


def get_user_message(error: Exception) -> str:
    """Convert technical error to user-friendly message.

    Provides helpful, actionable messages for users instead of raw
    exception details.

    Args:
        error: Exception to convert

    Returns:
        User-friendly error message with recovery suggestions

    Example:
        >>> try:
        ...     operation()
        ... except Exception as e:
        ...     print(get_user_message(e))
        "Connection failed. Please check your internet connection and try again."
    """
    error_class = classify_error(error)
    error_type = type(error).__name__
    error_msg = str(error)
    error_type_lower = error_type.lower()
    error_msg_lower = error_msg.lower()

    # Map error classes to their message generators
    if error_class == ErrorClass.TRANSIENT:
        return _get_transient_message(error_type_lower, error_msg_lower, error_msg)

    if error_class == ErrorClass.PERMANENT:
        return _get_permanent_message(error_type_lower, error_msg_lower, error_msg)

    if error_class == ErrorClass.DEGRADED:
        return _get_degraded_message(error_type_lower, error_msg_lower)

    return f"An unexpected error occurred: {error_type}. Please try again or contact support."


def _get_transient_message(error_type_lower: str, error_msg_lower: str, error_msg: str) -> str:
    """Get user message for transient errors."""
    if "timeout" in error_type_lower or "timeout" in error_msg_lower:
        return "The operation timed out. Please try again in a moment."

    if "connection" in error_type_lower or "connection" in error_msg_lower:
        return "Connection failed. Please check your internet connection and try again."

    if "429" in error_msg or "rate limit" in error_msg_lower:
        return "Too many requests. Please wait a moment before trying again."

    return "A temporary error occurred. Please try again in a moment."


def _get_permanent_message(error_type_lower: str, error_msg_lower: str, error_msg: str) -> str:
    """Get user message for permanent errors."""
    if "filenotfound" in error_type_lower or "not found" in error_msg_lower:
        return f"Required file not found: {error_msg}. Please check your configuration."

    if "permission" in error_type_lower or "permission" in error_msg_lower:
        return "Permission denied. Please check file permissions or run with appropriate access."

    if "value" in error_type_lower or "validation" in error_msg_lower:
        return f"Invalid input: {error_msg}. Please check your data and try again."

    if "config" in error_msg_lower:
        return "Configuration error. Please check your settings and try again."

    return f"An error occurred: {error_msg}. Please check your input and configuration."


def _get_degraded_message(error_type_lower: str, error_msg_lower: str) -> str:
    """Get user message for degraded service errors."""
    if "model" in error_type_lower or "model" in error_msg_lower:
        return "AI model is experiencing issues. Using simplified processing for now."

    if "memory" in error_type_lower or "memory" in error_msg_lower:
        return "System resources are low. Some features may be temporarily limited."

    return "Service is running with limited functionality. Some features may be unavailable."


def should_retry(error: Exception) -> bool:
    """Determine if an error should trigger a retry.

    Convenience function that returns True for transient errors.

    Args:
        error: Exception to evaluate

    Returns:
        True if error is transient and retry is recommended

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     if should_retry(e):
        ...         time.sleep(1)
        ...         risky_operation()
    """
    return classify_error(error) == ErrorClass.TRANSIENT


def should_use_fallback(error: Exception) -> bool:
    """Determine if an error should trigger fallback behavior.

    Convenience function that returns True for degraded service errors.

    Args:
        error: Exception to evaluate

    Returns:
        True if error indicates degraded service requiring fallback

    Example:
        >>> try:
        ...     ai_analysis()
        ... except Exception as e:
        ...     if should_use_fallback(e):
        ...         simple_analysis()  # Fallback to simpler method
    """
    return classify_error(error) == ErrorClass.DEGRADED
