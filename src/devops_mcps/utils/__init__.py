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

Artifactory utilities:
- artifactory.artifactory_auth: Artifactory authentication and configuration
- artifactory.artifactory_api: Core Artifactory API functions

Azure utilities:
- azure.azure_auth: Azure authentication and credential management
- azure.azure_compute: Virtual machine management
- azure.azure_containers: AKS cluster management
- azure.azure_subscriptions: Subscription management
"""

# Import utility functions from GitHub modules
from .github.github_client import initialize_github_client
from .github.github_converters import _to_dict, _handle_paginated_list
from .github.github_api import (
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

# Import utility functions from Artifactory modules
from .artifactory import (
  artifactory_list_items,
  artifactory_search_items,
  artifactory_get_item_info,
)

# Import utility functions from Azure modules
from .azure import (
  get_azure_credential,
  get_subscriptions,
  list_virtual_machines,
  list_aks_clusters,
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
  # Artifactory API functions
  "artifactory_list_items",
  "artifactory_search_items",
  "artifactory_get_item_info",
  # Azure API functions
  "get_azure_credential",
  "get_subscriptions",
  "list_virtual_machines",
  "list_aks_clusters",
  # GitHub utility modules (for direct access)
  "github_client",
  "github_converters",
  "github_api",
  # Jenkins utility modules (for direct access)
  "jenkins",
  # Artifactory utility modules (for direct access)
  "artifactory",
  # Azure utility modules (for direct access)
  "azure",
]

# Also import the modules themselves for direct access
from .github import github_client
from .github import github_converters
from .github import github_api
from . import jenkins
from . import artifactory
from . import azure
