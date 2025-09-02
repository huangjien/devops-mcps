"""
Jenkins job management module.
Handles operations related to Jenkins jobs.
"""

from typing import Any, Dict, List, Union

from jenkinsapi.custom_exceptions import JenkinsAPIException
from jenkinsapi.job import Job

from .client import get_jenkins_client
from .utils import _to_dict, validate_job_name
from ..cache import cache_manager as cache
import logging

logger = logging.getLogger(__name__)


def jenkins_get_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get all jobs from Jenkins.
    
    Returns:
        List of job dictionaries or error dictionary
    """
    logger.debug("jenkins_get_jobs called")
    
    # Check cache first
    cache_key = "jenkins:jobs:all"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_jobs: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        jobs = j.get_jobs()
        logger.debug(f"Found {len(jobs)} jobs.")
        result = [_to_dict(job) for job in jobs]
        cache.set(cache_key, result, ttl=600)  # Cache for 10 minutes
        return result
    except JenkinsAPIException as e:
        logger.error(f"jenkins_get_jobs Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_jobs: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_job_info(job_name: str) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Get detailed information about a specific job.
    
    Args:
        job_name: Name of the job to get information for
        
    Returns:
        Job information dictionary or error dictionary
    """
    logger.debug(f"jenkins_get_job_info called for job: {job_name}")
    
    if not validate_job_name(job_name):
        logger.error(f"Invalid job name: {job_name}")
        return {"error": f"Invalid job name: {job_name}"}
    
    # Check cache first
    cache_key = f"jenkins:job_info:{job_name}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_job_info: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        job: Job = j.get_job(job_name)
        result = _to_dict(job)
        cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        return result
    except JenkinsAPIException as e:
        if "No such job" in str(e):
            logger.warning(f"Job '{job_name}' not found.")
            return {"error": f"Job '{job_name}' not found."}
        logger.error(f"jenkins_get_job_info Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_job_info: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_job_builds(job_name: str, limit: int = 10) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get recent builds for a specific job.
    
    Args:
        job_name: Name of the job
        limit: Maximum number of builds to return
        
    Returns:
        List of build dictionaries or error dictionary
    """
    logger.debug(f"jenkins_get_job_builds called for job: {job_name}, limit: {limit}")
    
    if not validate_job_name(job_name):
        logger.error(f"Invalid job name: {job_name}")
        return {"error": f"Invalid job name: {job_name}"}
    
    if not isinstance(limit, int) or limit <= 0:
        logger.error(f"Invalid limit: {limit}")
        return {"error": f"Invalid limit: {limit}. Must be a positive integer."}
    
    # Check cache first
    cache_key = f"jenkins:job_builds:{job_name}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_job_builds: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        job: Job = j.get_job(job_name)
        builds = job.get_build_dict()
        
        # Get the most recent builds
        recent_builds = []
        for build_number in sorted(builds.keys(), reverse=True)[:limit]:
            build = job.get_build(build_number)
            recent_builds.append(_to_dict(build))
        
        cache.set(cache_key, recent_builds, ttl=300)  # Cache for 5 minutes
        return recent_builds
    except JenkinsAPIException as e:
        if "No such job" in str(e):
            logger.warning(f"Job '{job_name}' not found.")
            return {"error": f"Job '{job_name}' not found."}
        logger.error(f"jenkins_get_job_builds Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_job_builds: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}