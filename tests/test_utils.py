"""Tests for utility modules."""

import asyncio
import time

import pytest

from companion.utils import (
    CircuitBreaker,
    CircuitState,
    ErrorClass,
    classify_error,
    get_user_message,
    retry_with_backoff,
)
from companion.utils.circuit_breaker import CircuitBreakerError
from companion.utils.error_classifier import should_retry, should_use_fallback
from companion.utils.retry import retry_with_timeout

# Test retry_with_backoff


@pytest.mark.asyncio
async def test_retry_success_first_attempt():
    """Test successful function on first attempt."""
    call_count = 0

    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_with_backoff(success_func, max_retries=3)

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_success_after_failures():
    """Test successful function after some failures."""
    call_count = 0

    async def eventual_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            msg = "Temporary failure"
            raise ConnectionError(msg)
        return "success"

    result = await retry_with_backoff(eventual_success, max_retries=3, base_delay=0.01)

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausts_retries():
    """Test that all retries are exhausted before raising."""
    call_count = 0

    async def always_fails():
        nonlocal call_count
        call_count += 1
        msg = "Persistent error"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="Persistent error"):
        await retry_with_backoff(always_fails, max_retries=3, base_delay=0.01)

    assert call_count == 4  # Initial + 3 retries


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Test that delays increase exponentially."""
    delays = []
    start_times = []

    async def track_timing():
        start_times.append(time.time())
        if len(start_times) < 4:
            msg = "Temporary"
            raise ConnectionError(msg)
        return "done"

    await retry_with_backoff(track_timing, max_retries=3, base_delay=0.1, max_delay=1.0)

    # Calculate delays between attempts
    for i in range(1, len(start_times)):
        delays.append(start_times[i] - start_times[i - 1])

    # Each delay should be roughly double the previous (with some tolerance)
    assert delays[0] < delays[1]
    assert delays[1] < delays[2]


@pytest.mark.asyncio
async def test_retry_respects_max_delay():
    """Test that delay doesn't exceed max_delay."""
    call_count = 0

    async def fail_many_times():
        nonlocal call_count
        call_count += 1
        if call_count < 10:
            msg = "Temporary"
            raise ConnectionError(msg)
        return "done"

    # With base_delay=1.0 and max_delay=2.0, delays shouldn't exceed 2 seconds
    start = time.time()
    await retry_with_backoff(fail_many_times, max_retries=10, base_delay=1.0, max_delay=2.0)
    elapsed = time.time() - start

    # Should take less than 10 * 2 = 20 seconds
    assert elapsed < 20


@pytest.mark.asyncio
async def test_retry_with_specific_exceptions():
    """Test retry only catches specified exceptions."""
    call_count = 0

    async def fails_with_different_errors():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            msg = "Retry this"
            raise ConnectionError(msg)
        msg = "Don't retry this"
        raise ValueError(msg)

    # Should not retry ValueError
    with pytest.raises(ValueError, match="Don't retry this"):
        await retry_with_backoff(
            fails_with_different_errors,
            max_retries=3,
            base_delay=0.01,
            exceptions=(ConnectionError,),
        )

    assert call_count == 2  # Initial ConnectionError + ValueError


@pytest.mark.asyncio
async def test_retry_with_timeout_success():
    """Test retry_with_timeout for successful operation."""

    async def quick_op():
        await asyncio.sleep(0.1)
        return "done"

    result = await retry_with_timeout(quick_op, timeout=1.0, max_retries=2)
    assert result == "done"


@pytest.mark.asyncio
async def test_retry_with_timeout_exceeds():
    """Test retry_with_timeout when operation times out."""

    async def slow_op():
        await asyncio.sleep(2.0)
        return "done"

    with pytest.raises(TimeoutError):
        await retry_with_timeout(slow_op, timeout=0.5, max_retries=2, base_delay=0.01)


# Test CircuitBreaker


def test_circuit_breaker_initial_state():
    """Test circuit breaker starts in CLOSED state."""
    breaker = CircuitBreaker(failure_threshold=3)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.is_closed
    assert not breaker.is_open
    assert not breaker.is_half_open


def test_circuit_breaker_successful_call():
    """Test successful call through circuit breaker."""
    breaker = CircuitBreaker(failure_threshold=3)

    def success_func():
        return "success"

    result = breaker.call(success_func)

    assert result == "success"
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_opens_after_threshold():
    """Test circuit opens after failure threshold."""
    breaker = CircuitBreaker(failure_threshold=3, timeout=60)

    def failing_func():
        msg = "Failed"
        raise ConnectionError(msg)

    # Fail 3 times to reach threshold
    for _ in range(3):
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

    # Circuit should now be OPEN
    assert breaker.state == CircuitState.OPEN
    assert breaker.is_open


def test_circuit_breaker_blocks_when_open():
    """Test circuit breaker blocks requests when open."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=60)

    def failing_func():
        msg = "Failed"
        raise ConnectionError(msg)

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

    # Should now block requests
    with pytest.raises(CircuitBreakerError, match="OPEN"):
        breaker.call(failing_func)


def test_circuit_breaker_transitions_to_half_open():
    """Test circuit transitions to HALF_OPEN after timeout."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=1)

    def failing_func():
        msg = "Failed"
        raise ConnectionError(msg)

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

    assert breaker.is_open

    # Wait for timeout
    time.sleep(1.1)

    # Next call should transition to HALF_OPEN
    def success_func():
        return "success"

    result = breaker.call(success_func)

    assert result == "success"
    assert breaker.state == CircuitState.CLOSED  # Success closes circuit


def test_circuit_breaker_reopens_on_half_open_failure():
    """Test circuit reopens if HALF_OPEN attempt fails."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=1, half_open_attempts=1)

    def failing_func():
        msg = "Failed"
        raise ConnectionError(msg)

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

    # Wait for timeout
    time.sleep(1.1)

    # Fail during HALF_OPEN
    with pytest.raises(ConnectionError):
        breaker.call(failing_func)

    # Should reopen
    assert breaker.is_open


def test_circuit_breaker_reset():
    """Test manual circuit breaker reset."""
    breaker = CircuitBreaker(failure_threshold=2)

    def failing_func():
        msg = "Failed"
        raise ConnectionError(msg)

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

    assert breaker.is_open

    # Manual reset
    breaker.reset()

    assert breaker.is_closed
    assert breaker.failure_count == 0


# Test error classification


def test_classify_error_transient():
    """Test classification of transient errors."""
    transient_errors = [
        ConnectionError("Connection timeout"),
        TimeoutError("Operation timed out"),
        ConnectionError("Network unavailable"),
        Exception("503 Service unavailable"),
    ]

    for error in transient_errors:
        assert classify_error(error) == ErrorClass.TRANSIENT


def test_classify_error_permanent():
    """Test classification of permanent errors."""
    permanent_errors = [
        FileNotFoundError("File not found"),
        ValueError("Invalid value"),
        PermissionError("Permission denied"),
        KeyError("Key missing"),
    ]

    for error in permanent_errors:
        assert classify_error(error) == ErrorClass.PERMANENT


def test_classify_error_degraded():
    """Test classification of degraded service errors."""
    degraded_errors = [
        Exception("Model loading error"),
        MemoryError("Out of memory"),
        Exception("Inference slow"),
        Exception("502 Bad Gateway"),
    ]

    for error in degraded_errors:
        assert classify_error(error) == ErrorClass.DEGRADED


def test_get_user_message_transient():
    """Test user messages for transient errors."""
    msg = get_user_message(TimeoutError("Operation timed out"))
    assert "timed out" in msg.lower()
    assert "try again" in msg.lower()


def test_get_user_message_permanent():
    """Test user messages for permanent errors."""
    msg = get_user_message(FileNotFoundError("config.json not found"))
    assert "not found" in msg.lower()
    assert "configuration" in msg.lower()


def test_get_user_message_degraded():
    """Test user messages for degraded service errors."""
    msg = get_user_message(Exception("Model loading failed"))
    assert "model" in msg.lower() or "issues" in msg.lower()


def test_should_retry_transient():
    """Test should_retry returns True for transient errors."""
    assert should_retry(ConnectionError("Timeout"))
    assert should_retry(TimeoutError("Network"))


def test_should_retry_permanent():
    """Test should_retry returns False for permanent errors."""
    assert not should_retry(FileNotFoundError("Missing"))
    assert not should_retry(ValueError("Invalid"))


def test_should_use_fallback_degraded():
    """Test should_use_fallback returns True for degraded errors."""
    assert should_use_fallback(Exception("Model error"))
    assert should_use_fallback(MemoryError("Low memory"))


def test_should_use_fallback_other():
    """Test should_use_fallback returns False for non-degraded errors."""
    assert not should_use_fallback(FileNotFoundError("Missing"))
    assert not should_use_fallback(TimeoutError("Timeout"))
