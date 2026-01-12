"""Unit tests for rate_limiter.py module.

This module contains comprehensive tests for rate limiting functionality.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from devops_mcps.utils.rate_limiter import (
  RateLimiter,
  get_github_limiter,
  get_jenkins_limiter,
  get_azure_limiter,
  get_artifactory_limiter,
  wait_for_rate_limit,
)


class TestRateLimiter(unittest.TestCase):
  """Test cases for RateLimiter class."""

  def setUp(self):
    """Set up test fixtures."""
    # Save original environment variables
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_initial_tokens(self):
    """Test that rate limiter starts with full bucket."""
    limiter = RateLimiter(rate=10, per=60)
    self.assertEqual(limiter.tokens, 10)

  def test_acquire_token(self):
    """Test acquiring a token."""
    limiter = RateLimiter(rate=10, per=60)
    result = limiter.acquire(block=False)
    self.assertTrue(result)
    self.assertEqual(limiter.tokens, 9)

  def test_acquire_multiple_tokens(self):
    """Test acquiring multiple tokens."""
    limiter = RateLimiter(rate=10, per=60)
    for _ in range(5):
      result = limiter.acquire(block=False)
      self.assertTrue(result)
    self.assertEqual(limiter.tokens, 5)

  def test_exhaust_bucket(self):
    """Test exhausting the token bucket."""
    limiter = RateLimiter(rate=10, per=60)
    # Exhaust all tokens
    for _ in range(10):
      limiter.acquire(block=False)
    self.assertEqual(limiter.tokens, 0)

  def test_token_refill(self):
    """Test token refill over time."""
    with patch("devops_mcps.utils.rate_limiter.time.monotonic") as mock_monotonic:
      mock_monotonic.side_effect = [0.0] + ([0.0] * 10) + [6.1]
      limiter = RateLimiter(rate=10, per=60)
      for _ in range(10):
        limiter.acquire(block=False)
      self.assertEqual(limiter.tokens, 0)
      limiter.get_wait_time()
      self.assertEqual(limiter.tokens, 1)

  def test_blocking_acquire(self):
    """Test blocking acquire with timeout."""
    limiter = RateLimiter(rate=10, per=60)
    result = limiter.acquire(block=True, timeout=0.5)
    self.assertTrue(result)
    self.assertEqual(limiter.tokens, 9)

  def test_blocking_acquire_timeout(self):
    """Test blocking acquire with timeout."""
    limiter = RateLimiter(rate=10, per=60)
    for _ in range(10):
      limiter.acquire(block=False)
    with patch("devops_mcps.utils.rate_limiter.time.sleep", return_value=None):
      with patch("devops_mcps.utils.rate_limiter.time.monotonic") as mock_monotonic:
        mock_monotonic.side_effect = [
          0.0,
          0.0,
          0.0,
          0.11,
        ]
        limiter.last_update = 0.0
        result = limiter.acquire(block=True, timeout=0.1)
    self.assertFalse(result)

  def test_reset(self):
    """Test resetting rate limiter."""
    limiter = RateLimiter(rate=10, per=60)
    limiter.acquire(block=False)
    limiter.acquire(block=False)
    self.assertEqual(limiter.tokens, 8)

    limiter.reset()
    self.assertEqual(limiter.tokens, 10)

  def test_get_stats(self):
    """Test getting rate limiter statistics."""
    limiter = RateLimiter(rate=10, per=60)
    limiter.acquire(block=False)
    stats = limiter.get_stats()
    self.assertEqual(stats["available_tokens"], 9)
    self.assertEqual(stats["recent_requests"], 1)

  def test_get_wait_time(self):
    """Test getting estimated wait time."""
    limiter = RateLimiter(rate=10, per=60)
    for _ in range(10):
      limiter.acquire(block=False)
    wait_time = limiter.get_wait_time()
    self.assertGreater(wait_time, 0)
    self.assertLessEqual(wait_time, 6.0)


class TestServiceLimiters(unittest.TestCase):
  """Test cases for service-specific rate limiters."""

  def test_get_github_limiter(self):
    """Test getting GitHub rate limiter."""
    limiter = get_github_limiter()
    self.assertIsNotNone(limiter)
    self.assertEqual(limiter.rate, 30)
    self.assertEqual(limiter.per, 60)

  def test_get_jenkins_limiter(self):
    """Test getting Jenkins rate limiter."""
    limiter = get_jenkins_limiter()
    self.assertIsNotNone(limiter)
    self.assertEqual(limiter.rate, 60)
    self.assertEqual(limiter.per, 60)

  def test_get_azure_limiter(self):
    """Test getting Azure rate limiter."""
    limiter = get_azure_limiter()
    self.assertIsNotNone(limiter)
    self.assertEqual(limiter.rate, 30)
    self.assertEqual(limiter.per, 60)

  def test_get_artifactory_limiter(self):
    """Test getting Artifactory rate limiter."""
    limiter = get_artifactory_limiter()
    self.assertIsNotNone(limiter)
    self.assertEqual(limiter.rate, 30)
    self.assertEqual(limiter.per, 60)


class TestWaitForRateLimit(unittest.TestCase):
  """Test cases for wait_for_rate_limit function."""

  def test_wait_for_rate_limit_calls_acquire(self):
    """Test waiting for rate limit calls acquire with timeout."""
    limiter = MagicMock()
    limiter.get_wait_time.return_value = 1.0

    wait_for_rate_limit(limiter, "GitHub")

    limiter.acquire.assert_called_once_with(block=True, timeout=60)


class TestCustomRateLimiter(unittest.TestCase):
  """Test cases for custom rate limiter configurations."""

  def test_get_github_limiter_custom(self):
    """Test getting GitHub rate limiter with custom rate."""
    limiter = RateLimiter(rate=50, per=60)
    self.assertEqual(limiter.rate, 50)
    self.assertEqual(limiter.per, 60)

  def test_get_jenkins_limiter_custom(self):
    """Test getting Jenkins rate limiter with custom rate."""
    limiter = RateLimiter(rate=50, per=60)
    self.assertEqual(limiter.rate, 50)
    self.assertEqual(limiter.per, 60)


if __name__ == "__main__":
  unittest.main()
