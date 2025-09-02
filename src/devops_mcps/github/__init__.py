"""
GitHub API module - Modular interface for GitHub operations.

This module provides a comprehensive interface for interacting with GitHub,
organized into logical submodules for better maintainability and testability.
"""

from .github_client import (
    initialize_github_client,
    get_github_client,
    reset_github_client,
    g
)

from .github_repositories import (
    gh_search_repositories,
    gh_get_file_contents,
    gh_get_repository
)

from .github_issues import (
    gh_get_issue_content,
    gh_list_issues,
    gh_get_issue_details
)

from .github_commits import (
    gh_list_commits
)

from .github_search import (
    gh_search_code
)

from .github_serializers import (
    _to_dict,
    _handle_paginated_list
)

from .github_user import gh_get_current_user_info

# Export all public functions
__all__ = [
    # Client functions
    'initialize_github_client',
    'get_github_client',
    'reset_github_client',
    'g',
    
    # Repository functions
    'gh_search_repositories',
    'gh_get_file_contents',
    'gh_get_repository',
    
    # Issue functions
    'gh_get_issue_content',
    'gh_list_issues',
    'gh_get_issue_details',
    
    # Commit functions
    'gh_list_commits',
    
    # Search functions
    'gh_search_code',
    
    # Serializer functions
    '_to_dict',
    '_handle_paginated_list',
    
    # User functions
    'gh_get_current_user_info'
]