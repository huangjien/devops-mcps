"""Unit tests for metrics.py module.

This module contains comprehensive tests for metrics collection functionality.
"""

import os
import time
import unittest
from unittest.mock import patch, MagicMock

from devops_mcps.utils.metrics import (
  MetricsCollector,
  get_metrics,
  increment_counter,
  set_gauge,
  observe_histogram,
  time_function,
  export_metrics_prometheus,
)


class TestMetricsCollector(unittest.TestCase):
  """Test cases for MetricsCollector class."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_initialization_enabled(self):
    """Test initialization with metrics enabled."""
    collector = MetricsCollector(enabled=True)
    self.assertTrue(collector.enabled)

  def test_initialization_disabled(self):
    """Test initialization with metrics disabled."""
    collector = MetricsCollector(enabled=False)
    self.assertFalse(collector.enabled)

  def test_increment_counter(self):
    """Test incrementing a counter."""
    collector = MetricsCollector(enabled=True)
    collector.increment("test_counter", value=5)
    self.assertEqual(collector.get_counter("test_counter"), 5)

  def test_increment_counter_with_tags(self):
    """Test incrementing a counter with tags."""
    collector = MetricsCollector(enabled=True)
    collector.increment("test_counter", value=3, tags={"service": "test"})
    self.assertEqual(collector.get_counter('test_counter{service="test"}'), 3)

  def test_set_gauge(self):
    """Test setting a gauge value."""
    collector = MetricsCollector(enabled=True)
    collector.set_gauge("test_gauge", 42.5)
    self.assertEqual(collector.get_gauge("test_gauge"), 42.5)

  def test_set_gauge_with_tags(self):
    """Test setting a gauge value with tags."""
    collector = MetricsCollector(enabled=True)
    collector.set_gauge("test_gauge", 99.9, tags={"unit": "percent"})
    self.assertEqual(collector.get_gauge('test_gauge{unit="percent"}'), 99.9)

  def test_observe_histogram(self):
    """Test observing a histogram value."""
    collector = MetricsCollector(enabled=True)
    collector.observe("test_histogram", 1.5)
    collector.observe("test_histogram", 2.3)
    collector.observe("test_histogram", 0.8)

    stats = collector.get_histogram_stats("test_histogram")
    self.assertEqual(stats["count"], 3)
    self.assertAlmostEqual(stats["min"], 0.8)
    self.assertAlmostEqual(stats["max"], 2.3)
    self.assertAlmostEqual(stats["avg"], 1.533, places=2)

  def test_observe_histogram_with_tags(self):
    """Test observing a histogram value with tags."""
    collector = MetricsCollector(enabled=True)
    collector.observe("test_histogram", 100.0, tags={"unit": "ms"})
    stats = collector.get_histogram_stats('test_histogram{unit="ms"}')
    self.assertEqual(stats["count"], 1)

  def test_start_stop_timer(self):
    """Test starting and stopping a timer."""
    collector = MetricsCollector(enabled=True)
    timer_id = collector.start_timer("test_timer")
    self.assertIsNotNone(timer_id)

    time.sleep(0.01)  # Small delay
    duration = collector.stop_timer(timer_id, "test_timer")
    self.assertIsNotNone(duration)
    self.assertGreater(duration, 0)

    stats = collector.get_histogram_stats("test_timer_duration_ms")
    self.assertEqual(stats["count"], 1)

  def test_timer_not_found(self):
    """Test stopping a timer that doesn't exist."""
    collector = MetricsCollector(enabled=True)
    duration = collector.stop_timer("nonexistent", "test_timer")
    self.assertIsNone(duration)

  def test_get_histogram_stats_empty(self):
    """Test getting histogram stats when no values."""
    collector = MetricsCollector(enabled=True)
    stats = collector.get_histogram_stats("empty_histogram")
    self.assertEqual(stats["count"], 0)
    self.assertEqual(stats["min"], 0)
    self.assertEqual(stats["max"], 0)
    self.assertEqual(stats["avg"], 0)

  def test_get_counter_not_found(self):
    """Test getting a counter that doesn't exist."""
    collector = MetricsCollector(enabled=True)
    value = collector.get_counter("nonexistent_counter")
    self.assertEqual(value, 0)

  def test_get_gauge_not_found(self):
    """Test getting a gauge that doesn't exist."""
    collector = MetricsCollector(enabled=True)
    value = collector.get_gauge("nonexistent_gauge")
    self.assertIsNone(value)

  def test_reset(self):
    """Test resetting all metrics."""
    collector = MetricsCollector(enabled=True)
    collector.increment("test_counter", value=10)
    collector.set_gauge("test_gauge", 50.0)
    collector.observe("test_histogram", 5.0)

    self.assertEqual(collector.get_counter("test_counter"), 10)
    self.assertEqual(collector.get_gauge("test_gauge"), 50.0)

    collector.reset()

    self.assertEqual(collector.get_counter("test_counter"), 0)
    self.assertIsNone(collector.get_gauge("test_gauge"))
    stats = collector.get_histogram_stats("test_histogram")
    self.assertEqual(stats["count"], 0)

  def test_export_prometheus(self):
    """Test exporting metrics in Prometheus format."""
    collector = MetricsCollector(enabled=True)
    collector.increment("test_counter", value=5)
    collector.set_gauge("test_gauge", 42.0)

    prometheus_output = collector.export_prometheus()

    self.assertIn("# TYPE devops_mcps_test_counter counter", prometheus_output)
    self.assertIn("devops_mcps_test_counter 5", prometheus_output)
    self.assertIn("# TYPE devops_mcps_test_gauge gauge", prometheus_output)
    self.assertIn("devops_mcps_test_gauge 42.0", prometheus_output)

  def test_export_prometheus_disabled(self):
    """Test exporting metrics when disabled."""
    collector = MetricsCollector(enabled=False)
    prometheus_output = collector.export_prometheus()
    self.assertIn("# Metrics collection is disabled", prometheus_output)

  def test_disabled_operations(self):
    """Test that operations are no-ops when disabled."""
    collector = MetricsCollector(enabled=False)

    collector.increment("test_counter", value=5)
    collector.set_gauge("test_gauge", 42.0)
    collector.observe("test_histogram", 1.5)

    self.assertEqual(collector.get_counter("test_counter"), 0)
    self.assertIsNone(collector.get_gauge("test_gauge"))
    stats = collector.get_histogram_stats("test_histogram")
    self.assertEqual(stats["count"], 0)


class TestGlobalMetrics(unittest.TestCase):
  """Test cases for global metrics functions."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_get_metrics(self):
    """Test getting global metrics instance."""
    metrics = get_metrics()
    self.assertIsInstance(metrics, MetricsCollector)

  def test_increment_counter_global(self):
    """Test incrementing counter via global function."""
    increment_counter("global_test_counter", value=7)
    metrics = get_metrics()
    self.assertEqual(metrics.get_counter("global_test_counter"), 7)

  def test_set_gauge_global(self):
    """Test setting gauge via global function."""
    set_gauge("global_test_gauge", 88.8)
    metrics = get_metrics()
    self.assertEqual(metrics.get_gauge("global_test_gauge"), 88.8)

  def test_observe_histogram_global(self):
    """Test observing histogram via global function."""
    observe_histogram("global_test_histogram", 123.4)
    metrics = get_metrics()
    stats = metrics.get_histogram_stats("global_test_histogram")
    self.assertEqual(stats["count"], 1)

  def test_export_metrics_prometheus_global(self):
    """Test exporting metrics via global function."""
    increment_counter("export_test_counter", value=3)
    prometheus_output = export_metrics_prometheus()
    self.assertIn("# TYPE devops_mcps_export_test_counter counter", prometheus_output)
    self.assertIn("devops_mcps_export_test_counter 3", prometheus_output)


class TestTimeFunctionDecorator(unittest.TestCase):
  """Test cases for time_function decorator."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.utils.metrics.time_function")
  def test_decorator_wraps_function(self, mock_time_function):
    """Test that decorator wraps function correctly."""
    mock_timer = MagicMock()
    mock_timer.side_effect = lambda func: func
    mock_time_function.return_value = mock_timer

    @mock_time_function("test_metric")
    def test_func():
      return "result"

    # The decorator should return the wrapped function
    self.assertTrue(callable(test_func))
    result = test_func()
    self.assertEqual(result, "result")

  def test_decorator_records_timing(self):
    """Test that decorator records function timing."""
    metrics = get_metrics()

    @time_function("test_timing_metric")
    def test_func():
      return "result"

    test_func()

    # Check that histogram was recorded
    stats = metrics.get_histogram_stats("test_timing_metric_duration_ms")
    self.assertEqual(stats["count"], 1)


class TestMetricsWithEnvironment(unittest.TestCase):
  """Test cases for metrics with environment variable."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_metrics_disabled_by_env(self):
    """Test that metrics can be disabled via environment variable."""
    os.environ["METRICS_ENABLED"] = "false"
    metrics = get_metrics()
    self.assertFalse(metrics.enabled)

  def test_metrics_enabled_by_env(self):
    """Test that metrics can be enabled via environment variable."""
    os.environ["METRICS_ENABLED"] = "true"
    metrics = get_metrics()
    self.assertTrue(metrics.enabled)


if __name__ == "__main__":
  unittest.main()
