# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/__init__.py

# Import all tool modules
from . import github
from . import jenkins
from . import azure
from . import artifactory
from . import core
from . import utils

# Export all modules and their functions
__all__ = [
  # Main modules
  "github",
  "jenkins",
  "azure",
  "artifactory",
  "core",
  "utils",
  # GitHub functions (for backward compatibility)
  "initialize_github_client",
  "gh_get_current_user_info",
  "gh_search_repositories",
  "gh_get_file_contents",
  "gh_list_commits",
  "gh_list_issues",
  "gh_get_repository",
  "gh_search_code",
  "gh_get_issue_details",
  "gh_get_issue_content",
  # Jenkins functions (for backward compatibility)
  "initialize_jenkins_client",
  "jenkins_get_jobs",
  "jenkins_get_build_log",
  "jenkins_get_all_views",
  "jenkins_get_build_parameters",
  "jenkins_get_queue",
  "jenkins_get_recent_failed_builds",
  "set_jenkins_client_for_testing",
]

# Re-export GitHub functions for backward compatibility
from .github import (
  initialize_github_client,
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

# Re-export Jenkins functions for backward compatibility
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
