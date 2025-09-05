"""Jenkins Build API functions.

This module re-exports functions from the following modules:
- jenkins_helpers: Utility functions for accessing Jenkins client and constants
- jenkins_logs: Functions for retrieving build logs
- jenkins_parameters: Functions for retrieving build parameters
- jenkins_builds: Functions for retrieving build information
"""

import logging
from typing import List, Dict, Any, Union

# Re-export functions from new modules
from .jenkins_helpers import (
    _get_jenkins_client,
    _get_jenkins_constants,
    _get_to_dict,
    _get_cache,
    check_jenkins_credentials,
    # Constants
    JENKINS_URL,
    JENKINS_USER,
    JENKINS_TOKEN,
    LOG_LENGTH,
    j,
    cache
)
from .jenkins_logs import jenkins_get_build_log
from .jenkins_parameters import jenkins_get_build_parameters
from .jenkins_builds import jenkins_get_recent_failed_builds

logger = logging.getLogger(__name__)


# The implementation of jenkins_get_build_log has been moved to jenkins_logs.py




# The implementation of jenkins_get_build_parameters has been moved to jenkins_parameters.py


# The implementation of jenkins_get_recent_failed_builds has been moved to jenkins_builds.py