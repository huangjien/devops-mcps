"""Jenkins integration for DevOps MCPs."""

import logging
import requests
from typing import List, Optional, Dict, Any, Union

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
    JENKINS_TOKEN,
    JENKINS_USER,
    JENKINS_URL,
    j
)
from .cache import cache

logger = logging.getLogger(__name__)

# All Jenkins API functions are now imported from utils.jenkins
