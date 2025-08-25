"""
Production-ready resilience patterns for external service integration.

Implements circuit breaker, retry logic, timeout management, and graceful
degradation patterns for building robust RAG systems.
"""

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration parameters."""

    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: int = 60  # Seconds before attempting recovery
    success_threshold: int = 2  # Successes needed to close circuit
    timeout_seconds: float = 30.0  # Request timeout
    monitor_window: int = 300  # Sliding window for error rate (seconds)


@dataclass
class RetryConfig:
    """Retry configuration parameters."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay between retries
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add randomness to prevent thundering herd


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker operational metrics."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)

    def add_failure(self, error: str) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.total_failures += 1
        self.total_requests += 1
        self.last_failure_time = time.time()

    def add_success(self) -> None:
        """Record a success."""
        self.success_count += 1
        self.total_successes += 1
        self.total_requests += 1
        self.last_success_time = time.time()
        # Reset failure count on success in half-open state
        if self.state == CircuitState.HALF_OPEN:
            self.failure_count = 0

    def transition_to(self, new_state: CircuitState, reason: str = "") -> None:
        """Transition to new state with logging."""
        old_state = self.state
        self.state = new_state

        transition = {
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": time.time(),
            "reason": reason,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
        }
        self.state_transitions.append(transition)

        # Keep only last 50 transitions
        if len(self.state_transitions) > 50:
            self.state_transitions = self.state_transitions[-50:]

    def get_error_rate(self) -> float:
        """Calculate current error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.total_failures / self.total_requests

    def reset_counters(self) -> None:
        """Reset success/failure counters (used when transitioning states)."""
        self.success_count = 0
        self.failure_count = 0


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(
        self, service_name: str, state: CircuitState, correlation_id: str = ""
    ):
        self.service_name = service_name
        self.state = state
        self.correlation_id = correlation_id
        message = f"Circuit breaker is {state.value} for {service_name}"
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Prevents cascading failures by monitoring error rates and temporarily
    blocking requests when services are unhealthy.
    """

    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

        logger.info(
            f"Circuit breaker initialized for {service_name}",
            extra={
                "service_name": service_name,
                "failure_threshold": config.failure_threshold,
                "recovery_timeout": config.recovery_timeout,
            },
        )

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails
        """
        correlation_id = kwargs.get("correlation_id", "")

        async with self._lock:
            await self._update_state()

            # Block requests if circuit is open
            if self.metrics.state == CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker OPEN - blocking request to {self.service_name}",
                    extra={
                        "service_name": self.service_name,
                        "correlation_id": correlation_id,
                        "failure_count": self.metrics.failure_count,
                        "last_failure": self.metrics.last_failure_time,
                    },
                )
                raise CircuitBreakerError(
                    self.service_name, self.metrics.state, correlation_id
                )

        # Execute function with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout_seconds
            )

            # Record success
            async with self._lock:
                self.metrics.add_success()
                await self._check_recovery()

            logger.debug(
                f"Circuit breaker - successful call to {self.service_name}",
                extra={
                    "service_name": self.service_name,
                    "correlation_id": correlation_id,
                    "state": self.metrics.state.value,
                    "success_count": self.metrics.success_count,
                },
            )

            return result

        except asyncio.TimeoutError as e:
            async with self._lock:
                self.metrics.add_failure(
                    f"Timeout after {self.config.timeout_seconds}s"
                )
                await self._check_failure()

            logger.error(
                f"Circuit breaker - timeout in {self.service_name}",
                extra={
                    "service_name": self.service_name,
                    "correlation_id": correlation_id,
                    "timeout": self.config.timeout_seconds,
                    "failure_count": self.metrics.failure_count,
                },
            )
            raise

        except Exception as e:
            async with self._lock:
                self.metrics.add_failure(str(e))
                await self._check_failure()

            logger.error(
                f"Circuit breaker - failure in {self.service_name}: {str(e)}",
                extra={
                    "service_name": self.service_name,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "failure_count": self.metrics.failure_count,
                    "state": self.metrics.state.value,
                },
            )
            raise

    async def _update_state(self) -> None:
        """Update circuit state based on current conditions."""
        current_time = time.time()

        # Check if we should transition from OPEN to HALF_OPEN
        if (
            self.metrics.state == CircuitState.OPEN
            and current_time - self.metrics.last_failure_time
            >= self.config.recovery_timeout
        ):
            self.metrics.transition_to(
                CircuitState.HALF_OPEN,
                f"Recovery timeout ({self.config.recovery_timeout}s) elapsed",
            )
            self.metrics.reset_counters()

            logger.info(
                f"Circuit breaker transitioning to HALF_OPEN for {self.service_name}",
                extra={
                    "service_name": self.service_name,
                    "recovery_timeout": self.config.recovery_timeout,
                },
            )

    async def _check_failure(self) -> None:
        """Check if circuit should open due to failures."""
        if (
            self.metrics.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]
            and self.metrics.failure_count >= self.config.failure_threshold
        ):
            self.metrics.transition_to(
                CircuitState.OPEN,
                f"Failure threshold ({self.config.failure_threshold}) exceeded",
            )

            logger.warning(
                f"Circuit breaker OPENING for {self.service_name}",
                extra={
                    "service_name": self.service_name,
                    "failure_count": self.metrics.failure_count,
                    "threshold": self.config.failure_threshold,
                    "error_rate": self.metrics.get_error_rate(),
                },
            )

    async def _check_recovery(self) -> None:
        """Check if circuit should close due to successful recovery."""
        if (
            self.metrics.state == CircuitState.HALF_OPEN
            and self.metrics.success_count >= self.config.success_threshold
        ):
            self.metrics.transition_to(
                CircuitState.CLOSED,
                f"Success threshold ({self.config.success_threshold}) achieved",
            )
            self.metrics.reset_counters()

            logger.info(
                f"Circuit breaker CLOSED for {self.service_name} - service recovered",
                extra={
                    "service_name": self.service_name,
                    "success_count": self.metrics.success_count,
                    "threshold": self.config.success_threshold,
                },
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current circuit breaker metrics."""
        return {
            "service_name": self.service_name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_requests": self.metrics.total_requests,
            "total_failures": self.metrics.total_failures,
            "total_successes": self.metrics.total_successes,
            "error_rate": self.metrics.get_error_rate(),
            "last_failure_time": self.metrics.last_failure_time,
            "last_success_time": self.metrics.last_success_time,
            "recent_transitions": self.metrics.state_transitions[
                -5:
            ],  # Last 5 transitions
        }

    def force_state(self, state: CircuitState, reason: str = "Manual override") -> None:
        """Force circuit to specific state (for testing/management)."""
        logger.warning(
            f"Circuit breaker state forced to {state.value} for {self.service_name}",
            extra={"service_name": self.service_name, "reason": reason},
        )
        self.metrics.transition_to(state, reason)


class RetryHandler:
    """
    Exponential backoff retry handler for transient failures.

    Implements intelligent retry logic with jitter to prevent
    thundering herd problems and cascade failures.
    """

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        correlation_id: str = "",
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Function arguments
            correlation_id: Request correlation ID
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception encountered after all retries exhausted
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(
                    f"Retry attempt {attempt}/{self.config.max_attempts}",
                    extra={
                        "correlation_id": correlation_id,
                        "attempt": attempt,
                        "max_attempts": self.config.max_attempts,
                    },
                )

                result = await func(*args, **kwargs)

                if attempt > 1:
                    logger.info(
                        f"Retry succeeded on attempt {attempt}",
                        extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt,
                            "total_attempts": self.config.max_attempts,
                        },
                    )

                return result

            except Exception as e:
                last_exception = e

                logger.warning(
                    f"Retry attempt {attempt} failed: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "attempt": attempt,
                        "max_attempts": self.config.max_attempts,
                        "error": str(e),
                    },
                )

                # Don't retry on final attempt
                if attempt == self.config.max_attempts:
                    break

                # Don't retry certain types of errors
                if self._is_non_retryable_error(e):
                    logger.info(
                        f"Non-retryable error encountered, stopping retries: {str(e)}",
                        extra={
                            "correlation_id": correlation_id,
                            "error_type": type(e).__name__,
                        },
                    )
                    break

                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)

                logger.info(
                    f"Retrying in {delay:.2f} seconds",
                    extra={
                        "correlation_id": correlation_id,
                        "delay": delay,
                        "next_attempt": attempt + 1,
                    },
                )

                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            f"All {self.config.max_attempts} retry attempts failed",
            extra={
                "correlation_id": correlation_id,
                "max_attempts": self.config.max_attempts,
                "final_error": str(last_exception),
            },
        )

        # This should never happen as we have max_attempts >= 1, but satisfy mypy
        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError(
                "All retry attempts failed but no exception was captured"
            )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        # Exponential backoff: base_delay * (multiplier ^ (attempt - 1))
        delay = self.config.base_delay * (
            self.config.backoff_multiplier ** (attempt - 1)
        )

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter = delay * 0.1 * random.random()  # Up to 10% jitter
            delay += jitter

        return delay

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if error should not be retried."""
        # Authentication/authorization errors shouldn't be retried
        if (
            "authentication" in str(error).lower()
            or "unauthorized" in str(error).lower()
        ):
            return True
        if "forbidden" in str(error).lower() or "access denied" in str(error).lower():
            return True

        # Invalid input shouldn't be retried
        if "validation" in str(error).lower() or "invalid" in str(error).lower():
            return True

        # Circuit breaker errors shouldn't be retried
        if isinstance(error, CircuitBreakerError):
            return True

        return False


class ResilienceManager:
    """
    Central manager for resilience patterns across all external services.

    Manages circuit breakers, retry policies, and health monitoring
    for all external service integrations.
    """

    def __init__(self) -> None:
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}

        # Initialize service configurations
        self._setup_service_configs()

    def _setup_service_configs(self) -> None:
        """Setup resilience configurations for each service."""
        # Claude API - Conservative settings for paid API
        self.register_service(
            "claude_api",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2,
                timeout_seconds=60.0,
            ),
            RetryConfig(
                max_attempts=2,  # Conservative for paid API
                base_delay=1.0,
                max_delay=10.0,
            ),
        )

        # Pinecone - More aggressive retries for infrastructure service
        self.register_service(
            "pinecone",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                timeout_seconds=30.0,
            ),
            RetryConfig(
                max_attempts=3,
                base_delay=0.5,
                max_delay=30.0,
            ),
        )

        # Embedding APIs - Balance between cost and reliability
        self.register_service(
            "embedding_api",
            CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=45,
                success_threshold=2,
                timeout_seconds=30.0,
            ),
            RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=20.0,
            ),
        )

        # Redis - Fast recovery for caching service
        self.register_service(
            "redis",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=15,  # Quick recovery for cache
                success_threshold=2,
                timeout_seconds=5.0,  # Short timeout for cache operations
            ),
            RetryConfig(
                max_attempts=2,
                base_delay=0.1,
                max_delay=2.0,
            ),
        )

    def register_service(
        self,
        service_name: str,
        cb_config: CircuitBreakerConfig,
        retry_config: RetryConfig,
    ) -> None:
        """Register a service with resilience configuration."""
        self.circuit_breakers[service_name] = CircuitBreaker(service_name, cb_config)
        self.retry_configs[service_name] = retry_config

        logger.info(
            f"Registered resilience configuration for {service_name}",
            extra={
                "service_name": service_name,
                "failure_threshold": cb_config.failure_threshold,
                "max_retries": retry_config.max_attempts,
            },
        )

    async def execute_with_resilience(
        self,
        service_name: str,
        func: Callable[..., Any],
        *args: Any,
        correlation_id: str = "",
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with full resilience protection.

        Combines circuit breaker and retry logic for robust service calls.

        Args:
            service_name: Name of the service being called
            func: Async function to execute
            *args: Function arguments
            correlation_id: Request correlation ID
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        if service_name not in self.circuit_breakers:
            logger.warning(
                f"No resilience configuration for {service_name}, using defaults",
                extra={"service_name": service_name, "correlation_id": correlation_id},
            )
            # Use default configuration
            self.register_service(
                service_name,
                CircuitBreakerConfig(),
                RetryConfig(),
            )

        circuit_breaker = self.circuit_breakers[service_name]
        retry_config = self.retry_configs[service_name]
        retry_handler = RetryHandler(retry_config)

        # Create wrapped function that includes circuit breaker
        async def protected_func(*args: Any, **kwargs: Any) -> Any:
            return await circuit_breaker.call(func, *args, **kwargs)

        # Execute with retry logic
        return await retry_handler.execute(
            protected_func, *args, correlation_id=correlation_id, **kwargs
        )

    @asynccontextmanager
    async def resilient_call(
        self, service_name: str, correlation_id: str = ""
    ) -> AsyncGenerator[Callable[..., Awaitable[Any]], None]:
        """
        Context manager for resilient service calls.

        Usage:
            async with resilience_manager.resilient_call("pinecone") as call:
                result = await call(some_function, arg1, arg2)
        """

        async def call_wrapper(
            func: Callable[..., Any], *args: Any, **kwargs: Any
        ) -> Any:
            return await self.execute_with_resilience(
                service_name, func, *args, correlation_id=correlation_id, **kwargs
            )

        yield call_wrapper

    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Get health status for a specific service."""
        if service_name not in self.circuit_breakers:
            return {"service_name": service_name, "status": "unknown"}

        metrics = self.circuit_breakers[service_name].get_metrics()

        # Determine overall health status
        state = metrics["state"]
        error_rate = metrics["error_rate"]

        if state == "open":
            status = "unhealthy"
        elif state == "half_open":
            status = "recovering"
        elif error_rate > 0.1:  # More than 10% error rate
            status = "degraded"
        else:
            status = "healthy"

        return {
            **metrics,
            "status": status,
            "retry_config": {
                "max_attempts": self.retry_configs[service_name].max_attempts,
                "base_delay": self.retry_configs[service_name].base_delay,
            },
        }

    def get_overall_health(self) -> Dict[str, Any]:
        """Get health status for all registered services."""
        service_health = {}
        unhealthy_count = 0
        total_services = len(self.circuit_breakers)

        for service_name in self.circuit_breakers:
            health = self.get_service_health(service_name)
            service_health[service_name] = health

            if health["status"] in ["unhealthy", "recovering"]:
                unhealthy_count += 1

        # Determine overall system health
        if unhealthy_count == 0:
            overall_status = "healthy"
        elif unhealthy_count < total_services / 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "healthy_services": total_services - unhealthy_count,
            "total_services": total_services,
            "services": service_health,
        }

    def force_circuit_state(
        self, service_name: str, state: CircuitState, reason: str = "Manual override"
    ) -> None:
        """Force a circuit breaker to specific state (for testing/ops)."""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name].force_state(state, reason)
        else:
            logger.warning(f"Unknown service for circuit override: {service_name}")


# Global resilience manager instance
resilience_manager = ResilienceManager()


def resilient(service_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for making functions resilient with circuit breaker and retry logic.

    Usage:
        @resilient("pinecone")
        async def query_pinecone(query: str, correlation_id: str = ""):
            # Function implementation
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            correlation_id = kwargs.get("correlation_id", "")
            return await resilience_manager.execute_with_resilience(
                service_name, func, *args, correlation_id=correlation_id, **kwargs
            )

        return wrapper

    return decorator
