"""Utility modules for DevOps MCPS.

This package contains utility modules for various DevOps operations:

GitHub utilities:
- github_client: GitHub client initialization and authentication
- github_converters: Object conversion utilities
- github_api: Core GitHub API functions

Jenkins utilities:
- jenkins.jenkins_client: Jenkins client initialization and authentication
- jenkins.jenkins_converters: Object conversion utilities
- jenkins.jenkins_api: Core Jenkins API functions
"""

# Import utility functions from GitHub modules
from .github_client import initialize_github_client
from .github_converters import _to_dict, _handle_paginated_list
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

# Import utility functions from Jenkins modules
from .jenkins import (
    initialize_jenkins_client,
    jenkins_get_jobs,
    jenkins_get_build_log,
    jenkins_get_all_views,
    jenkins_get_build_parameters,
    jenkins_get_queue,
    jenkins_get_recent_failed_builds,
    set_jenkins_client_for_testing,
)

# Export all utility functions
__all__ = [
    # GitHub client utilities
    "initialize_github_client",
    
    # GitHub converter utilities
    "_to_dict",
    "_handle_paginated_list",
    
    # GitHub API functions
    "gh_get_current_user_info",
    "gh_search_repositories",
    "gh_get_file_contents",
    "gh_list_commits",
    "gh_list_issues",
    "gh_get_repository",
    "gh_search_code",
    "gh_get_issue_details",
    "gh_get_issue_content",
    
    # Jenkins API functions
    "initialize_jenkins_client",
    "jenkins_get_jobs",
    "jenkins_get_build_log",
    "jenkins_get_all_views",
    "jenkins_get_build_parameters",
    "jenkins_get_queue",
    "jenkins_get_recent_failed_builds",
    "set_jenkins_client_for_testing",
    
    # GitHub utility modules (for direct access)
    "github_client",
    "github_converters", 
    "github_api",
    
    # Jenkins utility modules (for direct access)
    "jenkins",
]

# Also import the modules themselves for direct access
from . import github_client
from . import github_converters
from . import github_api
from . import jenkins