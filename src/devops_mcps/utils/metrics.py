"""Metrics collection module for DevOps MCP Server.

This module provides metrics collection for tool usage and performance monitoring.
Metrics can be exported in Prometheus format for external monitoring.
"""

import logging
import os
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class MetricsCollector:
  """Collects and tracks metrics for MCP server operations.

  Attributes:
      counters: Dictionary of counters for events
      histograms: Dictionary of histograms for timing data
      gauges: Dictionary of gauges for current values
      lock: Thread lock for thread safety
      enabled: Whether metrics collection is enabled
  """

  def __init__(self, enabled: bool = True):
    """Initialize metrics collector.

    Args:
        enabled: Whether metrics collection is enabled (default: True)
    """
    self.counters: Dict[str, int] = defaultdict(int)
    self.histograms: Dict[str, List[float]] = defaultdict(list)
    self.gauges: Dict[str, float] = {}
    self.lock = threading.Lock()
    self.enabled = enabled
    self._start_times: Dict[str, float] = {}

  def increment(
    self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
  ) -> None:
    """Increment a counter metric.

    Args:
        name: Name of the counter
        value: Amount to increment by (default: 1)
        tags: Optional tags for the metric
    """
    if not self.enabled:
      return

    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      self.counters[metric_name] += value
    logger.debug(f"Counter incremented: {metric_name} +{value}")

  def set_gauge(
    self, name: str, value: float, tags: Optional[Dict[str, str]] = None
  ) -> None:
    """Set a gauge metric value.

    Args:
        name: Name of the gauge
        value: Value to set
        tags: Optional tags for the metric
    """
    if not self.enabled:
      return

    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      self.gauges[metric_name] = value
    logger.debug(f"Gauge set: {metric_name} = {value}")

  def observe(
    self, name: str, value: float, tags: Optional[Dict[str, str]] = None
  ) -> None:
    """Observe a value for a histogram metric.

    Args:
        name: Name of the histogram
        value: Value to observe
        tags: Optional tags for the metric
    """
    if not self.enabled:
      return

    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      self.histograms[metric_name].append(value)
    logger.debug(f"Histogram observed: {metric_name} = {value}")

  def start_timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
    """Start a timer for a metric.

    Args:
        name: Name of the metric
        tags: Optional tags for the metric

    Returns:
        str: Timer ID for stopping the timer
    """
    if not self.enabled:
      return ""

    timer_id = f"{name}_{id(self)}"
    self._format_metric_name(name, tags)
    with self.lock:
      self._start_times[timer_id] = time.time()
    return timer_id

  def stop_timer(
    self, timer_id: str, name: str, tags: Optional[Dict[str, str]] = None
  ) -> Optional[float]:
    """Stop a timer and record the duration.

    Args:
        timer_id: Timer ID from start_timer
        name: Name of the metric
        tags: Optional tags for the metric

    Returns:
        float: Duration in seconds, or None if timer not found
    """
    if not self.enabled:
      return None

    with self.lock:
      start_time = self._start_times.pop(timer_id, None)

    if start_time is None:
      logger.warning(f"Timer not found: {timer_id}")
      return None

    duration = time.time() - start_time
    self.observe(f"{name}_duration_ms", duration * 1000, tags)
    return duration

  def time_function(self, name: str) -> Callable[..., Any]:
    """Decorator to time function execution.

    Args:
        name: Name of the metric

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
      def wrapper(*args, **kwargs) -> Any:
        timer_id = self.start_timer(name)
        try:
          result = func(*args, **kwargs)
        finally:
          self.stop_timer(timer_id, name)
        return result

      return wrapper

    return decorator

  def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
    """Get counter value.

    Args:
        name: Name of the counter
        tags: Optional tags for the metric

    Returns:
        int: Counter value or 0 if not found
    """
    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      return self.counters.get(metric_name, 0)

  def get_histogram_stats(
    self, name: str, tags: Optional[Dict[str, str]] = None
  ) -> Dict[str, float]:
    """Get histogram statistics.

    Args:
        name: Name of the histogram
        tags: Optional tags for the metric

    Returns:
        Dict: Statistics (count, min, max, avg, p50, p95, p99)
    """
    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      values = self.histograms.get(metric_name, [])

    if not values:
      return {
        "count": 0.0,
        "min": 0.0,
        "max": 0.0,
        "avg": 0.0,
        "p50": 0.0,
        "p95": 0.0,
        "p99": 0.0,
      }

    sorted_values = sorted(values)
    count = len(sorted_values)
    return {
      "count": float(count),
      "min": float(sorted_values[0]) if count > 0 else 0.0,
      "max": float(sorted_values[-1]) if count > 0 else 0.0,
      "avg": float(sum(sorted_values) / count) if count > 0 else 0.0,
      "p50": float(sorted_values[count // 2]) if count > 0 else 0.0,
      "p95": float(sorted_values[int(count * 0.95)]) if count > 0 else 0.0,
      "p99": float(sorted_values[int(count * 0.99)]) if count > 0 else 0.0,
    }

  def get_gauge(
    self, name: str, tags: Optional[Dict[str, str]] = None
  ) -> Optional[float]:
    """Get gauge value.

    Args:
        name: Name of the gauge
        tags: Optional tags for the metric

    Returns:
        float: Gauge value or None if not found
    """
    metric_name = self._format_metric_name(name, tags)
    with self.lock:
      return self.gauges.get(metric_name)

  def reset(self) -> None:
    """Reset all metrics (for testing)."""
    with self.lock:
      self.counters.clear()
      self.histograms.clear()
      self.gauges.clear()
      self._start_times.clear()
    logger.debug("Metrics reset")

  def export_prometheus(self) -> str:
    """Export metrics in Prometheus text format.

    Returns:
        str: Metrics in Prometheus text format
    """
    if not self.enabled:
      return "# Metrics collection is disabled\n"

    lines = ["# DevOps MCP Server Metrics"]
    lines.append(f"# Generated at {datetime.now(UTC).isoformat()}")

    # Export counters
    for name, counter_value in sorted(self.counters.items()):
      lines.append(f"# TYPE devops_mcps_{name} counter")
      lines.append(f"devops_mcps_{name} {counter_value}")

    # Export gauges
    for name, gauge_value in sorted(self.gauges.items()):
      lines.append(f"# TYPE devops_mcps_{name} gauge")
      lines.append(f"devops_mcps_{name} {gauge_value}")

    # Export histograms
    for name, values in sorted(self.histograms.items()):
      if values:
        stats = self.get_histogram_stats(name)
        lines.append(f"# TYPE devops_mcps_{name} histogram")
        lines.append(f"devops_mcps_{name}_count {int(stats['count'])}")
        lines.append(f"devops_mcps_{name}_sum {sum(values)}")
        lines.append(f"devops_mcps_{name}_min {stats['min']}")
        lines.append(f"devops_mcps_{name}_max {stats['max']}")
        lines.append(f"devops_mcps_{name}_avg {stats['avg']}")
        lines.append(f'devops_mcps_{name}_bucket{{le="0.005"}} {stats["p50"]}')
        lines.append(f'devops_mcps_{name}_bucket{{le="0.05"}} {stats["p95"]}')
        lines.append(f'devops_mcps_{name}_bucket{{le="0.095"}} {stats["p99"]}')

    return "\n".join(lines)

  def _format_metric_name(
    self, name: str, tags: Optional[Dict[str, str]] = None
  ) -> str:
    """Format metric name with optional tags.

    Args:
        name: Base metric name
        tags: Optional tags dictionary

    Returns:
        str: Formatted metric name
    """
    if tags:
      tag_parts = [f'{k}="{v}"' for k, v in sorted(tags.items())]
      return f"{name}{{{','.join(tag_parts)}}}"
    return name


# Global metrics collector instance
def _get_metrics_enabled() -> bool:
  """Check if metrics are enabled via environment variable.

  Returns:
      bool: True if metrics are enabled
  """
  return os.environ.get("METRICS_ENABLED", "true").lower() == "true"

_METRICS_INSTANCE: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
  """Get the global metrics collector instance.

  Returns:
      MetricsCollector: Global metrics collector
  """
  global _METRICS_INSTANCE

  enabled = _get_metrics_enabled()
  if _METRICS_INSTANCE is None:
    _METRICS_INSTANCE = MetricsCollector(enabled=enabled)
    return _METRICS_INSTANCE

  if _METRICS_INSTANCE.enabled != enabled:
    _METRICS_INSTANCE = MetricsCollector(enabled=enabled)

  return _METRICS_INSTANCE


def increment_counter(
  name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
) -> None:
  """Increment a counter metric.

  Args:
        name: Name of the counter
        value: Amount to increment by (default: 1)
        tags: Optional tags for the metric
  """
  metrics = get_metrics()
  metrics.increment(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
  """Set a gauge metric value.

  Args:
        name: Name of the gauge
        value: Value to set
        tags: Optional tags for the metric
  """
  metrics = get_metrics()
  metrics.set_gauge(name, value, tags)


def observe_histogram(
  name: str, value: float, tags: Optional[Dict[str, str]] = None
) -> None:
  """Observe a value for a histogram metric.

  Args:
        name: Name of the histogram
        value: Value to observe
        tags: Optional tags for the metric
  """
  metrics = get_metrics()
  metrics.observe(name, value, tags)


def time_function(name: str) -> Callable[..., Any]:
  """Decorator to time function execution.

  Args:
        name: Name of the metric

  Returns:
        Callable: Decorated function
  """
  metrics = get_metrics()
  return metrics.time_function(name)


def export_metrics_prometheus() -> str:
  """Export metrics in Prometheus text format.

  Returns:
        str: Metrics in Prometheus text format
  """
  metrics = get_metrics()
  return metrics.export_prometheus()


# Export all public symbols
__all__ = [
  "MetricsCollector",
  "get_metrics",
  "increment_counter",
  "set_gauge",
  "observe_histogram",
  "time_function",
  "export_metrics_prometheus",
]
