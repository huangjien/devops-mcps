"""
Cache module for backward compatibility.
Re-exports cache_manager from github.cache to maintain existing imports.
"""

from .github.cache import cache_manager

# Re-export for backward compatibility
__all__ = ['cache_manager']