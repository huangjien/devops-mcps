# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/github.py
import logging
from typing import List, Optional, Dict, Any, Union

# Import utility functions from the utils package
from .utils.github.github_client import initialize_github_client, g, GITHUB_TOKEN
from .utils.github.github_api import (
  gh_get_current_user_info,
  gh_search_repositories,
  gh_get_file_contents,
  gh_list_commits,
  gh_list_issues,
  gh_get_repository,
  gh_search_code,
  gh_get_issue_details,
  gh_get_issue_content,
)

logger = logging.getLogger(__name__)

# Re-export functions for backward compatibility
__all__ = [
  "initialize_github_client",
  "g",
  "GITHUB_TOKEN",
  "gh_get_current_user_info",
  "gh_search_repositories",
  "gh_get_file_contents",
  "gh_list_commits",
  "gh_list_issues",
  "gh_get_repository",
  "gh_search_code",
  "gh_get_issue_details",
  "gh_get_issue_content",
  # Legacy aliases
  "search_repositories",
  "get_current_user_info",
  "get_file_contents",
  "list_commits",
  "list_issues",
  "get_repository",
  "search_code",
  "get_issue_details",
  "get_github_issue_content",
]


# Legacy function aliases for backward compatibility
def search_repositories(query: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Legacy alias for gh_search_repositories."""
  return gh_search_repositories(query)


def get_current_user_info() -> Dict[str, Any]:
  """Legacy alias for gh_get_current_user_info."""
  return gh_get_current_user_info()


def get_file_contents(
  owner: str, repo: str, path: str, branch: Optional[str] = None
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
  """Legacy alias for gh_get_file_contents."""
  return gh_get_file_contents(owner, repo, path, branch)


def list_commits(
  owner: str, repo: str, branch: Optional[str] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Legacy alias for gh_list_commits."""
  return gh_list_commits(owner, repo, branch)


def list_issues(
  owner: str,
  repo: str,
  state: str = "open",
  labels: Optional[List[str]] = None,
  sort: str = "created",
  direction: str = "desc",
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Legacy alias for gh_list_issues."""
  return gh_list_issues(owner, repo, state, labels, sort, direction)


def get_repository(owner: str, repo: str) -> Union[Dict[str, Any], Dict[str, str]]:
  """Legacy alias for gh_get_repository."""
  return gh_get_repository(owner, repo)


def search_code(
  q: str, sort: str = "indexed", order: str = "desc"
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Legacy alias for gh_search_code."""
  return gh_search_code(q, sort, order)


def get_issue_details(owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
  """Legacy alias for gh_get_issue_details."""
  return gh_get_issue_details(owner, repo, issue_number)


def get_github_issue_content(owner: str, repo: str, issue_number: int) -> dict:
  """Legacy alias for gh_get_issue_content."""
  return gh_get_issue_content(owner, repo, issue_number)
