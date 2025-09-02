"""
Jenkins API module - Modular interface for Jenkins operations.

This module provides a comprehensive interface for interacting with Jenkins,
organized into logical submodules for better maintainability and testability.
"""

from .client import (
    initialize_jenkins_client,
    get_jenkins_client,
    set_jenkins_client_for_testing,
    check_jenkins_config,
    get_jenkins_env_vars
)

from .jobs import (
    jenkins_get_jobs,
    jenkins_get_job_info,
    jenkins_get_job_builds
)

from .builds import (
    jenkins_get_build_info,
    jenkins_get_build_log,
    jenkins_get_build_parameters,
    jenkins_get_recent_failed_builds,
)

from .views import (
    jenkins_get_all_views,
    jenkins_get_view_info,
    jenkins_get_view_jobs
)

from .queue import (
    jenkins_get_queue,
    jenkins_get_queue_item,
    jenkins_cancel_queue_item
)

from .utils import (
    _to_dict,
    format_timestamp,
    calculate_time_window,
    validate_job_name,
    validate_build_number
)

# Export all public functions
__all__ = [
    # Client functions
    'initialize_jenkins_client',
    'get_jenkins_client',
    'set_jenkins_client_for_testing',
    'check_jenkins_config',
    'get_jenkins_env_vars',
    
    # Job functions
    'jenkins_get_jobs',
    'jenkins_get_job_info',
    'jenkins_get_job_builds',
    
    # Build functions
    'jenkins_get_build_info',
    'jenkins_get_build_log',
    'jenkins_get_build_parameters',
    'jenkins_get_recent_failed_builds',
    
    # View functions
    'jenkins_get_all_views',
    'jenkins_get_view_info',
    'jenkins_get_view_jobs',
    
    # Queue functions
    'jenkins_get_queue',
    'jenkins_get_queue_item',
    'jenkins_cancel_queue_item',
    
    # Utility functions
    '_to_dict',
    'format_timestamp',
    'calculate_time_window',
    'validate_job_name',
    'validate_build_number'
]