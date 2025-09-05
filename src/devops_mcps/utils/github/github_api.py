"""GitHub API functions.

This module serves as the main entry point for GitHub API functions,
re-exporting functions from specialized modules for different GitHub operations.
"""

# Import all functions from specialized modules
from .github_user_api import gh_get_current_user_info
from .github_repository_api import gh_get_file_contents, gh_get_repository
from .github_search_api import gh_search_repositories, gh_search_code
from .github_issue_api import gh_list_issues, gh_get_issue_details, gh_get_issue_content
from .github_commit_api import gh_list_commits
from .github_client import initialize_github_client
from .github_converters import _to_dict, _handle_paginated_list

# Re-export all functions for backward compatibility
__all__ = [
  "gh_get_current_user_info",
  "gh_search_repositories",
  "gh_get_file_contents",
  "gh_list_commits",
  "gh_list_issues",
  "gh_get_repository",
  "gh_search_code",
  "gh_get_issue_details",
  "gh_get_issue_content",
  "initialize_github_client",
  "_to_dict",
  "_handle_paginated_list",
]
