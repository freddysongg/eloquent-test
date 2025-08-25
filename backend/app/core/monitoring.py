"""
Production-ready error monitoring and alerting system for RAG pipeline.

Implements comprehensive monitoring, metrics collection, and alerting
hooks for tracking system health and operational excellence.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels for monitoring system."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics collected by monitoring system."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMING = "timing"


@dataclass
class ErrorEvent:
    """Error event data structure for monitoring."""

    timestamp: float
    service_name: str
    error_type: str
    error_message: str
    correlation_id: str = ""
    user_id: Optional[str] = None
    request_path: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error event to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "service_name": self.service_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "request_path": self.request_path,
            "stack_trace": self.stack_trace,
            "metadata": self.metadata,
        }


@dataclass
class AlertRule:
    """Alert rule configuration for monitoring conditions."""

    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    description: str
    cooldown_seconds: int = 300  # 5 minutes default
    enabled: bool = True
    last_triggered: float = 0
    trigger_count: int = 0


@dataclass
class HealthMetrics:
    """System health metrics collection."""

    timestamp: float
    service_name: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    error_rate: float
    throughput_rpm: float  # requests per minute
    circuit_breaker_state: str
    additional_metrics: Dict[str, Any] = field(default_factory=dict)


class ErrorMonitor:
    """
    Error monitoring and alerting system for production RAG pipeline.

    Tracks error patterns, generates alerts, and provides operational insights.
    """

    def __init__(self, max_events: int = 10000, alert_window_minutes: int = 15):
        self.max_events = max_events
        self.alert_window_seconds = alert_window_minutes * 60

        # Error tracking
        self.error_events: deque = deque(maxlen=max_events)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, List[float]] = defaultdict(list)

        # Health metrics
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Alert system
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Set[str] = set()
        self.alert_callbacks: List[Callable[[str, AlertSeverity, str], None]] = []

        # Setup default alert rules
        self._setup_default_alert_rules()

        logger.info(
            f"Error monitor initialized with {max_events} max events, {alert_window_minutes}min window"
        )

    def _setup_default_alert_rules(self) -> None:
        """Setup default alert rules for common error patterns."""

        # High error rate alert
        def high_error_rate(metrics: Dict[str, Any]) -> bool:
            recent_errors = self._get_recent_error_count(300)  # 5 minutes
            recent_requests = self._estimate_recent_requests(300)
            if recent_requests > 0:
                error_rate = recent_errors / recent_requests
                return error_rate > 0.1  # > 10% error rate
            return recent_errors > 10  # Or absolute count > 10

        self.alert_rules.append(
            AlertRule(
                name="high_error_rate",
                condition=high_error_rate,
                severity=AlertSeverity.HIGH,
                description="Error rate exceeded 10% in the last 5 minutes",
                cooldown_seconds=300,
            )
        )

        # Circuit breaker open alert
        def circuit_breaker_open(metrics: Dict[str, Any]) -> bool:
            from app.core.resilience import resilience_manager

            overall_health = resilience_manager.get_overall_health()
            return any(
                service["status"] == "unhealthy"
                for service in overall_health["services"].values()
            )

        self.alert_rules.append(
            AlertRule(
                name="circuit_breaker_open",
                condition=circuit_breaker_open,
                severity=AlertSeverity.CRITICAL,
                description="One or more circuit breakers are open",
                cooldown_seconds=180,
            )
        )

        # Repeated error pattern alert
        def repeated_error_pattern(metrics: Dict[str, Any]) -> bool:
            recent_errors = [
                event
                for event in self.error_events
                if time.time() - event.timestamp < 600  # 10 minutes
            ]

            # Group by error type and service
            error_groups: Dict[str, int] = defaultdict(int)
            for error in recent_errors:
                key = f"{error.service_name}:{error.error_type}"
                error_groups[key] += 1

            # Alert if any error pattern repeats > 5 times
            return any(count > 5 for count in error_groups.values())

        self.alert_rules.append(
            AlertRule(
                name="repeated_error_pattern",
                condition=repeated_error_pattern,
                severity=AlertSeverity.MEDIUM,
                description="Same error pattern repeated more than 5 times in 10 minutes",
                cooldown_seconds=600,
            )
        )

        # API degradation alert
        def api_degradation(metrics: Dict[str, Any]) -> bool:
            for service_name, health in self.health_metrics.items():
                if (
                    service_name in ["claude_api", "pinecone"]
                    and health.status == "degraded"
                ):
                    return True
            return False

        self.alert_rules.append(
            AlertRule(
                name="api_degradation",
                condition=api_degradation,
                severity=AlertSeverity.MEDIUM,
                description="Critical API service is in degraded state",
                cooldown_seconds=300,
            )
        )

    def record_error(
        self,
        service_name: str,
        error_type: str,
        error_message: str,
        correlation_id: str = "",
        **metadata: Any,
    ) -> None:
        """
        Record an error event for monitoring and alerting.

        Args:
            service_name: Name of the service where error occurred
            error_type: Type/category of the error
            error_message: Error message or description
            correlation_id: Request correlation ID
            **metadata: Additional error context
        """
        event = ErrorEvent(
            timestamp=time.time(),
            service_name=service_name,
            error_type=error_type,
            error_message=error_message,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        # Store error event
        self.error_events.append(event)

        # Update counters
        error_key = f"{service_name}:{error_type}"
        self.error_counts[error_key] += 1

        # Track error patterns
        pattern_key = hashlib.md5(f"{service_name}:{error_type}".encode()).hexdigest()[
            :8
        ]
        self.error_patterns[pattern_key].append(event.timestamp)

        # Keep only recent patterns
        cutoff = time.time() - self.alert_window_seconds
        self.error_patterns[pattern_key] = [
            ts for ts in self.error_patterns[pattern_key] if ts > cutoff
        ]

        logger.error(
            f"Error recorded in monitoring system: {service_name}:{error_type}",
            extra={
                "service_name": service_name,
                "error_type": error_type,
                "correlation_id": correlation_id,
                "pattern_key": pattern_key,
                **metadata,
            },
        )

        # Trigger alert evaluation
        asyncio.create_task(self._evaluate_alerts())

    def record_health_metrics(self, metrics: HealthMetrics) -> None:
        """Record health metrics for a service."""
        self.health_metrics[metrics.service_name] = metrics
        self.metric_history[metrics.service_name].append(metrics)

        logger.debug(
            f"Health metrics recorded for {metrics.service_name}",
            extra={
                "service_name": metrics.service_name,
                "status": metrics.status,
                "response_time": metrics.response_time_ms,
                "error_rate": metrics.error_rate,
            },
        )

    async def _evaluate_alerts(self) -> None:
        """Evaluate all alert rules and trigger alerts if conditions are met."""
        current_time = time.time()

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            # Check cooldown period
            if current_time - rule.last_triggered < rule.cooldown_seconds:
                continue

            try:
                # Evaluate rule condition
                if rule.condition({}):  # Pass empty metrics dict for now
                    await self._trigger_alert(rule)
                    rule.last_triggered = current_time
                    rule.trigger_count += 1

            except Exception as e:
                logger.error(
                    f"Error evaluating alert rule {rule.name}: {str(e)}",
                    extra={"rule_name": rule.name, "error": str(e)},
                )

    async def _trigger_alert(self, rule: AlertRule) -> None:
        """Trigger an alert based on rule conditions."""
        alert_id = f"{rule.name}_{int(time.time())}"
        self.active_alerts.add(alert_id)

        alert_message = f"ALERT: {rule.description}"

        logger.warning(
            f"Alert triggered: {rule.name}",
            extra={
                "alert_id": alert_id,
                "rule_name": rule.name,
                "severity": rule.severity.value,
                "description": rule.description,
                "trigger_count": rule.trigger_count,
            },
        )

        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_id, rule.severity, alert_message)
            except Exception as e:
                logger.error(f"Alert callback failed: {str(e)}")

        # Log to structured alert log for external systems
        alert_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_id": alert_id,
            "rule_name": rule.name,
            "severity": rule.severity.value,
            "description": rule.description,
            "trigger_count": rule.trigger_count,
            "system_metrics": self._get_current_system_metrics(),
        }

        # This could be sent to external alerting systems (PagerDuty, Slack, etc.)
        logger.info(
            f"ALERT_JSON: {json.dumps(alert_data)}",
            extra={"alert_data": alert_data},
        )

    def register_alert_callback(
        self, callback: Callable[[str, AlertSeverity, str], None]
    ) -> None:
        """Register callback function for alert notifications."""
        self.alert_callbacks.append(callback)
        logger.info(f"Alert callback registered: {callback.__name__}")

    def add_custom_alert_rule(self, rule: AlertRule) -> None:
        """Add custom alert rule to monitoring system."""
        self.alert_rules.append(rule)
        logger.info(
            f"Custom alert rule added: {rule.name}",
            extra={"rule_name": rule.name, "severity": rule.severity.value},
        )

    def _get_recent_error_count(self, window_seconds: int) -> int:
        """Get count of errors in recent time window."""
        cutoff = time.time() - window_seconds
        return sum(1 for event in self.error_events if event.timestamp > cutoff)

    def _estimate_recent_requests(self, window_seconds: int) -> int:
        """Estimate recent request count from health metrics."""
        total_requests = 0
        for metrics in self.health_metrics.values():
            if time.time() - metrics.timestamp < window_seconds:
                # Rough estimate based on throughput
                total_requests += int(metrics.throughput_rpm * (window_seconds / 60))
        return max(total_requests, 1)  # Avoid division by zero

    def _get_current_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics snapshot."""
        from app.core.resilience import resilience_manager

        return {
            "error_count_5min": self._get_recent_error_count(300),
            "active_errors": len(self.error_events),
            "service_health": {
                name: {
                    "status": metrics.status,
                    "response_time": metrics.response_time_ms,
                    "error_rate": metrics.error_rate,
                }
                for name, metrics in self.health_metrics.items()
            },
            "circuit_breakers": resilience_manager.get_overall_health()["services"],
            "alert_rules_active": len([r for r in self.alert_rules if r.enabled]),
        }

    def get_error_summary(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get error summary for specified time window."""
        cutoff = time.time() - (window_minutes * 60)
        recent_errors = [e for e in self.error_events if e.timestamp > cutoff]

        # Group errors by service and type
        error_breakdown: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for error in recent_errors:
            error_breakdown[error.service_name][error.error_type] += 1

        # Top error patterns
        top_errors = sorted(
            [
                (service, error_type, count)
                for service, errors in error_breakdown.items()
                for error_type, count in errors.items()
            ],
            key=lambda x: x[2],
            reverse=True,
        )[:10]

        return {
            "window_minutes": window_minutes,
            "total_errors": len(recent_errors),
            "unique_error_types": len(
                set(f"{e.service_name}:{e.error_type}" for e in recent_errors)
            ),
            "services_affected": len(set(e.service_name for e in recent_errors)),
            "error_breakdown": dict(error_breakdown),
            "top_errors": [
                {"service": service, "error_type": error_type, "count": count}
                for service, error_type, count in top_errors
            ],
            "alert_rules_triggered": sum(r.trigger_count for r in self.alert_rules),
            "active_alerts": len(self.active_alerts),
        }

    def get_system_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system health dashboard data."""
        current_time = time.time()

        # Service health status
        service_status = {}
        for name, metrics in self.health_metrics.items():
            age_seconds = current_time - metrics.timestamp
            service_status[name] = {
                "status": metrics.status,
                "response_time_ms": metrics.response_time_ms,
                "error_rate": metrics.error_rate,
                "throughput_rpm": metrics.throughput_rpm,
                "circuit_breaker_state": metrics.circuit_breaker_state,
                "last_updated": age_seconds,
                "is_stale": age_seconds > 300,  # 5 minutes
            }

        # Alert summary
        alert_summary = {
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules if r.enabled]),
            "active_alerts": len(self.active_alerts),
            "recent_triggers": sum(
                1
                for r in self.alert_rules
                if current_time - r.last_triggered < 3600  # 1 hour
            ),
        }

        return {
            "timestamp": current_time,
            "system_status": "healthy",  # Could be computed based on services
            "services": service_status,
            "alerts": alert_summary,
            "errors_last_hour": self.get_error_summary(60),
            "circuit_breakers": self._get_circuit_breaker_summary(),
        }

    def _get_circuit_breaker_summary(self) -> Dict[str, Any]:
        """Get circuit breaker status summary."""
        from app.core.resilience import resilience_manager

        try:
            overall_health = resilience_manager.get_overall_health()
            return {
                "overall_status": overall_health["overall_status"],
                "healthy_services": overall_health["healthy_services"],
                "total_services": overall_health["total_services"],
                "service_details": overall_health["services"],
            }
        except Exception as e:
            logger.error(f"Failed to get circuit breaker summary: {str(e)}")
            return {"error": str(e)}


# Global error monitor instance
error_monitor = ErrorMonitor()


def track_error(
    service_name: str,
    error_type: str,
    error_message: str,
    correlation_id: str = "",
    **metadata: Any,
) -> None:
    """
    Convenience function to track errors in the global monitor.

    Usage:
        track_error("pinecone", "timeout", "Query timeout after 30s", correlation_id="123")
    """
    error_monitor.record_error(
        service_name, error_type, error_message, correlation_id, **metadata
    )


def track_health_metrics(
    service_name: str,
    status: str,
    response_time_ms: float,
    error_rate: float,
    throughput_rpm: float,
    circuit_breaker_state: str,
    **additional_metrics: Any,
) -> None:
    """
    Convenience function to track health metrics.

    Usage:
        track_health_metrics("claude_api", "healthy", 150.0, 0.02, 45.5, "closed")
    """
    metrics = HealthMetrics(
        timestamp=time.time(),
        service_name=service_name,
        status=status,
        response_time_ms=response_time_ms,
        error_rate=error_rate,
        throughput_rpm=throughput_rpm,
        circuit_breaker_state=circuit_breaker_state,
        additional_metrics=additional_metrics,
    )
    error_monitor.record_health_metrics(metrics)


# Example alert callback for logging
def log_alert_callback(alert_id: str, severity: AlertSeverity, message: str) -> None:
    """Example alert callback that logs alerts."""
    logger.warning(
        f"ALERT CALLBACK: {alert_id}",
        extra={
            "alert_id": alert_id,
            "severity": severity.value,
            "message": message,
        },
    )


# Register default callback
error_monitor.register_alert_callback(log_alert_callback)
