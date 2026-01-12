"""Rate limiting module for DevOps MCP Server.

This module implements token bucket algorithm for rate limiting API calls
to external services (GitHub, Jenkins, Azure, Artifactory).
"""

import logging
import os
import time
import threading
from typing import Optional, Dict
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
  """Token bucket rate limiter.

  This implements the token bucket algorithm for rate limiting.
  Each service can have its own rate limit configuration.

  Attributes:
      rate: Number of requests allowed per time window
      per: Time window in seconds
      tokens: Current number of available tokens
      last_update: Last time tokens were updated
      lock: Thread lock for thread safety
  """

  def __init__(self, rate: int = 30, per: int = 60):
    """Initialize rate limiter.

    Args:
        rate: Number of requests allowed per time window (default: 30)
        per: Time window in seconds (default: 60)
    """
    self.rate = rate
    self.per = per
    self.tokens = rate  # Start with full bucket
    self.last_update = time.time()
    self.lock = threading.Lock()
    self._request_times: deque = deque(maxlen=rate)

  def acquire(self, block: bool = True, timeout: Optional[float] = None) -> bool:
    """Acquire a token from the bucket.

    Args:
        block: If True, block until token is available
        timeout: Maximum time to wait for token (None = wait forever)

    Returns:
        bool: True if token acquired, False if timeout or would block
    """
    with self.lock:
      now = time.time()
      # Refill tokens based on elapsed time
      elapsed = now - self.last_update
      if elapsed > 0:
        # Calculate new tokens to add (use integer division to avoid floating point issues)
        new_tokens = int((elapsed / self.per) * self.rate)
        self.tokens = min(self.rate, self.tokens + new_tokens)
        self.last_update = now

      # Check if token is available
      if self.tokens >= 1:
        self.tokens -= 1
        self._request_times.append(now)
        return True

      if not block:
        return False

      # Wait for token to become available
      if timeout is not None:
        wait_time = timeout
      else:
        # Calculate time until next token
        wait_time = (self.per / self.rate) - elapsed
        if wait_time <= 0:
          # Should have token now, try again
          return self.acquire(block=True, timeout=timeout)
        wait_time = min(wait_time, timeout if timeout else wait_time)

      self.lock.release()
      time.sleep(wait_time)
      return self.acquire(block=True, timeout=timeout if timeout else None)

  def get_wait_time(self) -> float:
    """Get estimated wait time for next request.

    Returns:
        float: Estimated wait time in seconds
    """
    with self.lock:
      now = time.time()
      elapsed = now - self.last_update
      if elapsed > 0:
        new_tokens = (elapsed / self.per) * self.rate
        current_tokens = min(self.rate, self.tokens + new_tokens)
      else:
        current_tokens = self.tokens

      if current_tokens >= 1:
        return 0.0
      # Calculate time until next token (use integer division)
      return (self.per / self.rate) - int(elapsed)

  def reset(self) -> None:
    """Reset the rate limiter (for testing)."""
    with self.lock:
      self.tokens = self.rate
      self.last_update = time.time()
      self._request_times.clear()

  def get_stats(self) -> Dict[str, int]:
    """Get rate limiter statistics.

    Returns:
        Dict with statistics: available_tokens, recent_requests
    """
    with self.lock:
      return {
        "available_tokens": int(self.tokens),
        "recent_requests": len(self._request_times),
      }


# Global rate limiters for different services
# Default limits (can be overridden by environment variables)
_GITHUB_RATE = int(os.environ.get("GITHUB_RATE_LIMIT", "30"))
_GITHUB_PER = int(os.environ.get("GITHUB_RATE_PER", "60"))

_JENKINS_RATE = int(os.environ.get("JENKINS_RATE_LIMIT", "60"))
_JENKINS_PER = int(os.environ.get("JENKINS_RATE_PER", "60"))

_AZURE_RATE = int(os.environ.get("AZURE_RATE_LIMIT", "30"))
_AZURE_PER = int(os.environ.get("AZURE_RATE_PER", "60"))

_ARTIFACTORY_RATE = int(os.environ.get("ARTIFACTORY_RATE_LIMIT", "30"))
_ARTIFACTORY_PER = int(os.environ.get("ARTIFACTORY_RATE_PER", "60"))

# Create rate limiters
github_limiter = RateLimiter(rate=_GITHUB_RATE, per=_GITHUB_PER)
jenkins_limiter = RateLimiter(rate=_JENKINS_RATE, per=_JENKINS_PER)
azure_limiter = RateLimiter(rate=_AZURE_RATE, per=_AZURE_PER)
artifactory_limiter = RateLimiter(rate=_ARTIFACTORY_RATE, per=_ARTIFACTORY_PER)


def get_github_limiter() -> RateLimiter:
  """Get the GitHub rate limiter instance.

  Returns:
      RateLimiter: GitHub rate limiter
  """
  return github_limiter


def get_jenkins_limiter() -> RateLimiter:
  """Get the Jenkins rate limiter instance.

  Returns:
      RateLimiter: Jenkins rate limiter
  """
  return jenkins_limiter


def get_azure_limiter() -> RateLimiter:
  """Get the Azure rate limiter instance.

  Returns:
      RateLimiter: Azure rate limiter
  """
  return azure_limiter


def get_artifactory_limiter() -> RateLimiter:
  """Get the Artifactory rate limiter instance.

  Returns:
      RateLimiter: Artifactory rate limiter
  """
  return artifactory_limiter


def wait_for_rate_limit(limiter: RateLimiter, service_name: str) -> None:
  """Wait for rate limit to allow next request.

  Args:
      limiter: Rate limiter instance
      service_name: Name of the service (for logging)
  """
  wait_time = limiter.get_wait_time()
  if wait_time > 0:
    logger.info(
      f"Rate limit reached for {service_name}. "
      f"Waiting {wait_time:.2f} seconds before next request."
    )
    limiter.acquire(block=True)


# Export all public symbols
__all__ = [
  "RateLimiter",
  "get_github_limiter",
  "get_jenkins_limiter",
  "get_azure_limiter",
  "get_artifactory_limiter",
  "wait_for_rate_limit",
]
