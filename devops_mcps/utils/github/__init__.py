"""GitHub utilities package."""

# Import from main API module (which re-exports from specialized modules)
from .github_api import (
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

# Import utility functions
from .github_client import initialize_github_client
from .github_converters import _to_dict, _handle_paginated_list

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
