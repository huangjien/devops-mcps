"""GitHub operations module.

This module provides a unified interface for GitHub operations by importing
and exposing functions from specialized sub-modules.
"""

# Import Github class and exceptions for compatibility
from github import Github, GithubException, UnknownObjectException, BadCredentialsException, RateLimitExceededException

# Import all functions from the github module
from .github import (
    # Client functions
    initialize_github_client,
    get_github_client,
    reset_github_client,
    g,
    
    # Repository functions
    gh_search_repositories,
    gh_get_file_contents,
    gh_get_repository,
    
    # Issue functions
    gh_get_issue_content,
    gh_list_issues,
    gh_get_issue_details,
    
    # Commit functions
    gh_list_commits,
    
    # Search functions
    gh_search_code,
    
    # Serializer functions
    _to_dict,
    _handle_paginated_list
)

# Import input classes for wrapper functions


# Import user functions (keeping the original implementation for now)
import logging




logger = logging.getLogger(__name__)





# Export all functions for backward compatibility
__all__ = [
    # Github class and exceptions
    'Github',
    'GithubException',
    'UnknownObjectException', 
    'BadCredentialsException',
    'RateLimitExceededException',
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
    # User functions
    # Utility functions
    '_to_dict',
    '_handle_paginated_list'
]
