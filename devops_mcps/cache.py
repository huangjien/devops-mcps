"""In-memory cache module for DevOps MCP Server."""

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class CacheManager:
  """In-memory cache manager for MCP server."""

  def __init__(self):
    """Initialize in-memory cache."""
    self._cache: Dict[str, Dict[str, Any]] = {}
    self._lock = threading.Lock()
    self.default_ttl = 600  # 1 hour default
    logger.info("Initialized in-memory cache")

  def get(self, key: str) -> Optional[Any]:
    """Get cached value by key."""
    with self._lock:
      item = self._cache.get(key)
      if item:
        if datetime.now() < item["expires"]:
          return item["value"]
        # Auto cleanup expired item
        del self._cache[key]
      return None

  def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set cached value with optional TTL."""
    with self._lock:
      ttl = ttl if ttl is not None else self.default_ttl
      self._cache[key] = {
        "value": value,
        "expires": datetime.now() + timedelta(seconds=ttl),
      }
      return True

  def delete(self, key: str) -> bool:
    """Delete cached value."""
    with self._lock:
      if key in self._cache:
        del self._cache[key]
        return True
      return False

  def clear(self) -> None:
    """Clear all cached values."""
    with self._lock:
      self._cache.clear()


# Global cache instance
cache = CacheManager()
