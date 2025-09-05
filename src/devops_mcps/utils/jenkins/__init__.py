"""Jenkins utility modules.

This package contains utility modules for Jenkins operations:
- jenkins_client: Client initialization and authentication
- jenkins_converters: Object conversion utilities
- jenkins_api: Core Jenkins API functions
"""

from .jenkins_client import (
  initialize_jenkins_client,
  set_jenkins_client_for_testing,
  JENKINS_URL,
  JENKINS_USER,
  JENKINS_TOKEN,
  LOG_LENGTH,
  j,
)

from .jenkins_converters import _to_dict

from .jenkins_api import (
  jenkins_get_jobs,
  jenkins_get_build_log,
  jenkins_get_all_views,
  jenkins_get_build_parameters,
  jenkins_get_queue,
  jenkins_get_recent_failed_builds,
)

__all__ = [
  # Client
  "initialize_jenkins_client",
  "set_jenkins_client_for_testing",
  "JENKINS_URL",
  "JENKINS_USER",
  "JENKINS_TOKEN",
  "LOG_LENGTH",
  "j",
  # Converters
  "_to_dict",
  # API functions
  "jenkins_get_jobs",
  "jenkins_get_build_log",
  "jenkins_get_all_views",
  "jenkins_get_build_parameters",
  "jenkins_get_queue",
  "jenkins_get_recent_failed_builds",
]
