"""Jenkins Build API functions.

This module re-exports functions from the following modules:
- jenkins_helpers: Utility functions for accessing Jenkins client and constants
- jenkins_logs: Functions for retrieving build logs
- jenkins_parameters: Functions for retrieving build parameters
- jenkins_builds: Functions for retrieving build information
"""

import logging

# Re-export functions from new modules
from .jenkins_logs import jenkins_get_build_log
from .jenkins_parameters import jenkins_get_build_parameters
from .jenkins_builds import jenkins_get_recent_failed_builds

logger = logging.getLogger(__name__)

__all__ = [
    "jenkins_get_build_log",
    "jenkins_get_build_parameters",
    "jenkins_get_recent_failed_builds",
]
