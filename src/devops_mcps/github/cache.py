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
cache_manager = CacheManager()


def cache(expire: int = 600):
  """Decorator for caching function results.
  
  Args:
      expire: Cache expiration time in seconds (default: 600)
  """
  def decorator(func):
    def wrapper(*args, **kwargs):
      # Create cache key from function name and arguments
      cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
      
      # Try to get from cache first
      cached_result = cache_manager.get(cache_key)
      if cached_result is not None:
        return cached_result
      
      # Execute function and cache result
      # Handle functions that take input objects vs string arguments
      if args and hasattr(args[0], '__dict__'):
          # Input object case - call implementation directly
          result = func(args[0])
      elif args and isinstance(args[0], str):
          # String arguments case - this should be handled by wrapper functions
          # For backward compatibility, convert to input object and call implementation
          func_name = func.__name__.replace('gh_', '')
          
          if func_name == 'search_code':
              from .inputs import SearchCodeInput
              input_data = SearchCodeInput(
                  q=args[0],
                  sort=kwargs.get('sort', 'indexed'),
                  order=kwargs.get('order', 'desc'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'search_repositories':
              from .inputs import SearchRepositoriesInput
              input_data = SearchRepositoriesInput(
                  query=args[0],
                  sort=kwargs.get('sort', 'updated'),
                  order=kwargs.get('order', 'desc'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'get_repository' and len(args) >= 2:
              from .inputs import GetRepositoryInput
              input_data = GetRepositoryInput(
                  owner=args[0],
                  repo=args[1]
              )
              result = func(input_data)
          elif func_name == 'list_issues' and len(args) >= 2:
              from .inputs import ListIssuesInput
              input_data = ListIssuesInput(
                  owner=args[0],
                  repo=args[1],
                  state=kwargs.get('state', 'open'),
                  labels=kwargs.get('labels'),
                  sort=kwargs.get('sort', 'created'),
                  direction=kwargs.get('direction', 'desc'),
                  since=kwargs.get('since'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'list_commits' and len(args) >= 2:
              from .inputs import ListCommitsInput
              input_data = ListCommitsInput(
                  owner=args[0],
                  repo=args[1],
                  sha=kwargs.get('sha'),
                  path=kwargs.get('path'),
                  author=kwargs.get('author'),
                  since=kwargs.get('since'),
                  until=kwargs.get('until'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'get_file_contents' and len(args) >= 3:
              from .inputs import GetFileContentsInput
              input_data = GetFileContentsInput(
                  owner=args[0],
                  repo=args[1],
                  path=args[2],
                  branch=kwargs.get('ref')
              )
              result = func(input_data)
          elif func_name == 'get_issue_details' and len(args) >= 3:
              from .inputs import GetIssueDetailsInput
              input_data = GetIssueDetailsInput(
                  owner=args[0],
                  repo=args[1],
                  issue_number=args[2]
              )
              result = func(input_data)
          elif func_name == 'get_issue_content' and len(args) >= 3:
              from .inputs import GetIssueContentInput
              input_data = GetIssueContentInput(
                  owner=args[0],
                  repo=args[1],
                  issue_number=args[2],
                  include_comments=kwargs.get('include_comments', True),
                  max_comments=kwargs.get('max_comments', 100)
              )
              result = func(input_data)
          elif func_name == 'get_issue_content' and len(args) >= 3:
              from .inputs import GetIssueContentInput
              input_data = GetIssueContentInput(
                  owner=args[0],
                  repo=args[1],
                  issue_number=args[2],
                  include_comments=kwargs.get('include_comments', True),
                  max_comments=kwargs.get('max_comments', 50)
              )
              result = func(input_data)
          else:
              # Fallback to direct call
              result = func(*args, **kwargs)
      elif args:
          # Other cases
          result = func(args[0])
      else:
          # No arguments case - handle functions that require input objects
          func_name = func.__name__.replace('gh_', '')
          if func_name == 'get_current_user_info':
              from .inputs import GetCurrentUserInfoInput
              input_data = GetCurrentUserInfoInput()
              result = func(input_data)
          else:
              result = func()
      cache_manager.set(cache_key, result, expire)
      return result
    
    return wrapper
  return decorator


def github_cache(expire: int = 600):
  """Decorator for caching GitHub function results with custom key format.
  
  Args:
      expire: Cache expiration time in seconds (default: 600)
  """
  def decorator(func):
    def wrapper(*args, **kwargs):
      # Generate GitHub-specific cache key
      if args and hasattr(args[0], '__dict__'):
        # Handle input data objects
        input_data = args[0]
        func_name = func.__name__.replace('gh_', '')
        
        if func_name == 'search_code':
          cache_key = f"github:search_code:{input_data.q}:{input_data.sort}:{input_data.order}"
        elif func_name == 'search_repositories':
          cache_key = f"github:search_repositories:{input_data.query}:{input_data.sort}:{input_data.order}"
        elif func_name == 'get_repository':
          cache_key = f"github:get_repository:{input_data.owner}:{input_data.repo}"
        elif func_name == 'list_issues':
          cache_key = f"github:list_issues:{input_data.owner}:{input_data.repo}:{input_data.state or 'open'}"
        elif func_name == 'list_commits':
          cache_key = f"github:list_commits:{input_data.owner}:{input_data.repo}:{input_data.branch or 'main'}"
        elif func_name == 'get_file_contents':
          cache_key = f"github:get_file_contents:{input_data.owner}:{input_data.repo}:{input_data.path}"
        elif func_name == 'get_issue_details':
          cache_key = f"github:get_issue_details:{input_data.owner}:{input_data.repo}:{input_data.issue_number}"
        elif func_name == 'get_issue_content':
          cache_key = f"github:get_issue_content:{input_data.owner}:{input_data.repo}:{input_data.issue_number}"
        elif func_name == 'get_current_user_info':
          cache_key = "github:get_current_user_info"
        else:
          # Fallback to default format
          cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
      elif args and isinstance(args[0], str):
        # Handle string arguments (for backward compatibility wrapper functions)
        func_name = func.__name__.replace('gh_', '')
        
        if func_name == 'search_code':
          # For search_code, the first argument is the query string
          cache_key = f"github:search_code:{args[0]}:{kwargs.get('sort', 'indexed')}:{kwargs.get('order', 'desc')}"
        elif func_name == 'search_repositories':
          cache_key = f"github:search_repositories:{args[0]}:{kwargs.get('sort', 'updated')}:{kwargs.get('order', 'desc')}"
        elif func_name == 'get_repository':
          # For get_repository, args should be (owner, repo)
          if len(args) >= 2:
            cache_key = f"github:get_repository:{args[0]}:{args[1]}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        elif func_name == 'list_issues':
          # For list_issues, args should be (owner, repo)
          if len(args) >= 2:
            cache_key = f"github:list_issues:{args[0]}:{args[1]}:{kwargs.get('state', 'open')}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        elif func_name == 'list_commits':
          # For list_commits, args should be (owner, repo)
          if len(args) >= 2:
            cache_key = f"github:list_commits:{args[0]}:{args[1]}:{kwargs.get('branch', 'main')}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        elif func_name == 'get_file_contents':
          # For get_file_contents, args should be (owner, repo, path)
          if len(args) >= 3:
            cache_key = f"github:get_file_contents:{args[0]}:{args[1]}:{args[2]}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        elif func_name == 'get_issue_details':
          # For get_issue_details, args should be (owner, repo, issue_number)
          if len(args) >= 3:
            cache_key = f"github:get_issue_details:{args[0]}:{args[1]}:{args[2]}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        elif func_name == 'get_issue_content':
          # For get_issue_content, args should be (owner, repo, issue_number)
          if len(args) >= 3:
            cache_key = f"github:get_issue_content:{args[0]}:{args[1]}:{args[2]}"
          else:
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        else:
          # Fallback to default format
          cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
      else:
        # Fallback to default format
        cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
      
      # Try to get from cache first
      cached_result = cache_manager.get(cache_key)
      if cached_result is not None:
        return cached_result
      
      # Execute function and cache result
      # Handle functions that take input objects vs string arguments
      if args and hasattr(args[0], '__dict__'):
          # Input object case - call implementation directly
          result = func(args[0])
      elif args and isinstance(args[0], str):
          # String arguments case - this should be handled by wrapper functions
          # For backward compatibility, convert to input object and call implementation
          func_name = func.__name__.replace('gh_', '')
          
          if func_name == 'search_code':
              from .inputs import SearchCodeInput
              input_data = SearchCodeInput(
                  q=args[0],
                  sort=kwargs.get('sort', 'indexed'),
                  order=kwargs.get('order', 'desc'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'search_repositories':
              from .inputs import SearchRepositoriesInput
              input_data = SearchRepositoriesInput(
                  query=args[0],
                  sort=kwargs.get('sort', 'updated'),
                  order=kwargs.get('order', 'desc'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'get_repository' and len(args) >= 2:
              from .inputs import GetRepositoryInput
              input_data = GetRepositoryInput(
                  owner=args[0],
                  repo=args[1]
              )
              result = func(input_data)
          elif func_name == 'list_issues' and len(args) >= 2:
              from .inputs import ListIssuesInput
              input_data = ListIssuesInput(
                  owner=args[0],
                  repo=args[1],
                  state=kwargs.get('state', 'open'),
                  labels=kwargs.get('labels'),
                  sort=kwargs.get('sort', 'created'),
                  direction=kwargs.get('direction', 'desc'),
                  since=kwargs.get('since'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'list_commits' and len(args) >= 2:
              from .inputs import ListCommitsInput
              input_data = ListCommitsInput(
                  owner=args[0],
                  repo=args[1],
                  sha=kwargs.get('sha'),
                  path=kwargs.get('path'),
                  author=kwargs.get('author'),
                  since=kwargs.get('since'),
                  until=kwargs.get('until'),
                  per_page=kwargs.get('per_page', 30),
                  page=kwargs.get('page', 1)
              )
              result = func(input_data)
          elif func_name == 'get_file_contents' and len(args) >= 3:
              from .inputs import GetFileContentsInput
              input_data = GetFileContentsInput(
                  owner=args[0],
                  repo=args[1],
                  path=args[2],
                  branch=kwargs.get('ref')
              )
              result = func(input_data)
          elif func_name == 'get_issue_details' and len(args) >= 3:
              from .inputs import GetIssueDetailsInput
              input_data = GetIssueDetailsInput(
                  owner=args[0],
                  repo=args[1],
                  issue_number=args[2]
              )
              result = func(input_data)
          elif func_name == 'get_issue_content' and len(args) >= 3:
              from .inputs import GetIssueContentInput
              input_data = GetIssueContentInput(
                  owner=args[0],
                  repo=args[1],
                  issue_number=args[2],
                  include_comments=kwargs.get('include_comments', True),
                  max_comments=kwargs.get('max_comments', 100)
              )
              result = func(input_data)
          else:
              # Fallback to direct call
              result = func(*args, **kwargs)
      elif args:
          # Other cases
          result = func(args[0])
      else:
          # No arguments case - handle functions that require input objects
          func_name = func.__name__.replace('gh_', '')
          if func_name == 'get_current_user_info':
              from .inputs import GetCurrentUserInfoInput
              input_data = GetCurrentUserInfoInput()
              result = func(input_data)
          else:
              result = func()
      cache_manager.set(cache_key, result, expire)
      return result
    
    return wrapper
  return decorator


# Export both the decorator and manager for different use cases
# cache function is the decorator, cache_manager is the instance
