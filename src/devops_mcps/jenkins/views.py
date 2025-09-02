"""
Jenkins views management module.
Handles operations related to Jenkins views.
"""

from typing import Any, Dict, List, Union

from jenkinsapi.custom_exceptions import JenkinsAPIException

from .client import get_jenkins_client
from .utils import _to_dict
from ..cache import cache_manager as cache
import logging

logger = logging.getLogger(__name__)


def jenkins_get_all_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get all views from Jenkins.
    
    Returns:
        List of view dictionaries or error dictionary
    """
    logger.debug("jenkins_get_all_views called")
    
    # Check cache first
    cache_key = "jenkins:views:all"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_all_views: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        view_names = j.views.keys()
        logger.debug(f"Found {len(view_names)} views.")
        result = [_to_dict(view_name) for view_name in view_names]
        cache.set(cache_key, result, ttl=600)  # Cache for 10 minutes
        return result
    except JenkinsAPIException as e:
        logger.error(f"jenkins_get_all_views Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_all_views: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_view_info(view_name: str) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Get detailed information about a specific view.
    
    Args:
        view_name: Name of the view
        
    Returns:
        View information dictionary or error dictionary
    """
    logger.debug(f"jenkins_get_view_info called for view: {view_name}")
    
    if not view_name or not isinstance(view_name, str):
        logger.error(f"Invalid view name: {view_name}")
        return {"error": f"Invalid view name: {view_name}"}
    
    # Check cache first
    cache_key = f"jenkins:view_info:{view_name}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_view_info: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        view = j.get_view(view_name)
        result = _to_dict(view)
        cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        return result
    except JenkinsAPIException as e:
        if "No such view" in str(e) or "View not found" in str(e):
            logger.warning(f"View '{view_name}' not found.")
            return {"error": f"View '{view_name}' not found."}
        logger.error(f"jenkins_get_view_info Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_view_info: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_view_jobs(view_name: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get jobs belonging to a specific view.
    
    Args:
        view_name: Name of the view
        
    Returns:
        List of job dictionaries or error dictionary
    """
    logger.debug(f"jenkins_get_view_jobs called for view: {view_name}")
    
    if not view_name or not isinstance(view_name, str):
        logger.error(f"Invalid view name: {view_name}")
        return {"error": f"Invalid view name: {view_name}"}
    
    # Check cache first
    cache_key = f"jenkins:view_jobs:{view_name}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_view_jobs: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        view = j.get_view(view_name)
        jobs = view.get_job_dict()
        
        result = []
        for job_name, job in jobs.items():
            job_info = _to_dict(job)
            job_info["name"] = job_name
            result.append(job_info)
        
        cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        return result
    except JenkinsAPIException as e:
        if "No such view" in str(e) or "View not found" in str(e):
            logger.warning(f"View '{view_name}' not found.")
            return {"error": f"View '{view_name}' not found."}
        logger.error(f"jenkins_get_view_jobs Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_view_jobs: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}