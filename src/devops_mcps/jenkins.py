"""Jenkins integration for DevOps MCPs."""

import logging

# Internal imports
from .utils.jenkins import (
  initialize_jenkins_client,
  set_jenkins_client_for_testing,
  jenkins_get_jobs,
  jenkins_get_build_log,
  jenkins_get_all_views,
  jenkins_get_build_parameters,
  jenkins_get_queue,
  jenkins_get_recent_failed_builds,
  _to_dict,
)

# Also re-export the Jenkins client and configuration constants so importing
# `devops_mcps.jenkins` provides the client object `j` expected elsewhere in
# the package (for example in `server_setup.initialize_clients`).
from .utils.jenkins import (
  j,
  JENKINS_URL,
  JENKINS_USER,
  JENKINS_TOKEN,
  LOG_LENGTH,
)

logger = logging.getLogger(__name__)

# Re-export Jenkins utilities for backward compatibility
__all__ = [
  "initialize_jenkins_client",
  "set_jenkins_client_for_testing",
  "jenkins_get_jobs",
  "jenkins_get_build_log",
  "jenkins_get_all_views",
  "jenkins_get_build_parameters",
  "jenkins_get_queue",
  "jenkins_get_recent_failed_builds",
  "_to_dict",
  # Re-exported client and config
  "j",
  "JENKINS_URL",
  "JENKINS_USER",
  "JENKINS_TOKEN",
  "LOG_LENGTH",
]
