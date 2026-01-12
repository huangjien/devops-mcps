"""Jenkins API functions.

This module provides a unified interface to all Jenkins API functions.
Functions are organized into separate modules but re-exported here for backward compatibility.
"""

# Import all functions from specialized modules
from .jenkins_job_api import jenkins_get_jobs
from .jenkins_logs import jenkins_get_build_log
from .jenkins_parameters import jenkins_get_build_parameters
from .jenkins_builds import jenkins_get_recent_failed_builds
from .jenkins_view_api import jenkins_get_all_views
from .jenkins_queue_api import jenkins_get_queue

# Import constants from jenkins_client for backward compatibility
from .jenkins_client import (
  JENKINS_URL as _JENKINS_URL,
  JENKINS_USER as _JENKINS_USER,
  JENKINS_TOKEN as _JENKINS_TOKEN,
  LOG_LENGTH as _LOG_LENGTH,
  j as _j,
)

# Import cache and helpers for backward compatibility (moved to top to satisfy Ruff E402)
from ...cache import cache
import requests
from .jenkins_converters import _to_dict

# Make constants available at module level for patching
JENKINS_URL = _JENKINS_URL
JENKINS_USER = _JENKINS_USER
JENKINS_TOKEN = _JENKINS_TOKEN
LOG_LENGTH = _LOG_LENGTH
j = _j

# (imports were moved above to satisfy E402)

# Re-export all functions and constants for backward compatibility
__all__ = [
  # API functions
  "jenkins_get_jobs",
  "jenkins_get_build_log",
  "jenkins_get_build_parameters",
  "jenkins_get_recent_failed_builds",
  "jenkins_get_all_views",
  "jenkins_get_queue",
  # Constants and client
  "JENKINS_URL",
  "JENKINS_USER",
  "JENKINS_TOKEN",
  "LOG_LENGTH",
  "j",
  "cache",
  "requests",
  "_to_dict",
]
