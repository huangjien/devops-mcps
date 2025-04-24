"""Tests for cache module."""

import pytest
import time
import threading
from devops_mcps.cache import CacheManager


@pytest.fixture
def cache():
  """Fixture providing a clean CacheManager instance."""
  return CacheManager()


def test_cache_set_get(cache):
  """Test basic set/get operations."""
  cache.set("test_key", "test_value")
  assert cache.get("test_key") == "test_value"


def test_cache_expiration(cache):
  """Test TTL expiration."""
  cache.set("temp_key", "temp_value", ttl=1)  # 1 second TTL
  assert cache.get("temp_key") == "temp_value"
  time.sleep(1.1)  # Wait for expiration
  assert cache.get("temp_key") is None


def test_cache_delete(cache):
  """Test delete operation."""
  cache.set("delete_key", "delete_value")
  assert cache.delete("delete_key") is True
  assert cache.get("delete_key") is None
  assert cache.delete("non_existent_key") is False


def test_cache_clear(cache):
  """Test clear operation."""
  cache.set("key1", "value1")
  cache.set("key2", "value2")
  cache.clear()
  assert cache.get("key1") is None
  assert cache.get("key2") is None


def test_thread_safety(cache):
  """Test thread safety with concurrent access."""
  results = []

  def worker():
    for i in range(100):
      cache.set(f"key_{i}", i)
      results.append(cache.get(f"key_{i}"))

  threads = [threading.Thread(target=worker) for _ in range(10)]
  for t in threads:
    t.start()
  for t in threads:
    t.join()

  assert len(results) == 1000
  assert all(isinstance(x, int) for x in results)
