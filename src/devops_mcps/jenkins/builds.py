"""
Jenkins build management module.
Handles operations related to Jenkins builds.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone

import requests
from jenkinsapi.custom_exceptions import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build

from .client import get_jenkins_client
from .utils import _to_dict, validate_job_name, validate_build_number
from ..cache import cache_manager as cache
import logging

logger = logging.getLogger(__name__)


def jenkins_get_build_info(job_name: str, build_number: int) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Get information about a specific build.
    
    Args:
        job_name: Name of the job
        build_number: Build number
        
    Returns:
        Build information dictionary or error dictionary
    """
    logger.debug(f"jenkins_get_build_info called for job: {job_name}, build: {build_number}")
    
    if not validate_job_name(job_name):
        logger.error(f"Invalid job name: {job_name}")
        return {"error": f"Invalid job name: {job_name}"}
    
    if not validate_build_number(build_number):
        logger.error(f"Invalid build number: {build_number}")
        return {"error": f"Invalid build number: {build_number}"}
    
    # Check cache first
    cache_key = f"jenkins:build_info:{job_name}:{build_number}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_build_info: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        job: Job = j.get_job(job_name)
        build: Optional[Build] = job.get_build(build_number)
        
        if not build:
            logger.warning(f"Build #{build_number} not found for job {job_name}")
            return {"error": f"Build #{build_number} not found for job {job_name}"}
        
        result = _to_dict(build)
        cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        return result
    except JenkinsAPIException as e:
        if "No such job" in str(e):
            logger.warning(f"Job '{job_name}' not found.")
            return {"error": f"Job '{job_name}' not found."}
        logger.error(f"jenkins_get_build_info Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_build_info: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_build_log(job_name: str, build_number: int) -> Union[str, Dict[str, str]]:
    """
    Get the console log for a specific build.
    
    Args:
        job_name: Name of the job
        build_number: Build number (0 means get the latest build)
        
    Returns:
        Build log string or error dictionary
    """
    logger.debug(f"jenkins_get_build_log called for job: {job_name}, build: {build_number}")
    
    if not validate_job_name(job_name):
        logger.error(f"Invalid job name: {job_name}")
        return {"error": f"Invalid job name: {job_name}"}
    
    if not validate_build_number(build_number):
        logger.error(f"Invalid build number: {build_number}")
        return {"error": f"Invalid build number: {build_number}"}
    
    # Check cache first
    cache_key = f"jenkins:build_log:{job_name}:{build_number}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_build_log: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        job: Job = j.get_job(job_name)
        
        # Handle special case: build_number 0 means get the latest build
        if build_number == 0:
            latest_build_number = job.get_last_buildnumber()
            logger.debug(f"Getting latest build for job {job_name}: {latest_build_number}")
            build: Optional[Build] = job.get_build(latest_build_number)
        else:
            build: Optional[Build] = job.get_build(build_number)
        
        if not build:
            logger.warning(f"Build #{build_number} not found for job {job_name}")
            return {"error": f"Build #{build_number} not found for job {job_name}"}
        
        log = build.get_console()
        
        # Sanitize control characters by replacing them with spaces
        if isinstance(log, str):
            import re
            # Replace control characters (ASCII 0-31, except newline, tab, etc.) with spaces
            log = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', log)
        
        cache.set(cache_key, log, ttl=300)  # Cache for 5 minutes
        return log
    except JenkinsAPIException as e:
        if "No such job" in str(e):
            logger.warning(f"Job '{job_name}' not found.")
            return {"error": f"Job '{job_name}' not found."}
        logger.error(f"jenkins_get_build_log Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_build_log: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_build_parameters(job_name: str, build_number: int) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Get parameters for a specific build.
    
    Args:
        job_name: Name of the job
        build_number: Build number
        
    Returns:
        Build parameters dictionary or error dictionary
    """
    logger.debug(f"jenkins_get_build_parameters called for job: {job_name}, build: {build_number}")
    
    if not validate_job_name(job_name):
        logger.error(f"Invalid job name: {job_name}")
        return {"error": f"Invalid job name: {job_name}"}
    
    if not validate_build_number(build_number):
        logger.error(f"Invalid build number: {build_number}")
        return {"error": f"Invalid build number: {build_number}"}
    
    # Check cache first
    cache_key = f"jenkins:build_parameters:{job_name}:{build_number}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_build_parameters: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        job: Job = j.get_job(job_name)
        build: Optional[Build] = job.get_build(build_number)
        
        if not build:
            logger.warning(f"Build #{build_number} not found for job {job_name}")
            return {"error": f"Build #{build_number} not found for job {job_name}"}
        
        params: Dict[str, Any] = build.get_params()
        logger.debug(f"Retrieved parameters for build {job_name}#{build_number}: {params}")
        cache.set(cache_key, params, ttl=3600)  # Cache for 1 hour
        return params
    except JenkinsAPIException as e:
        if "No such job" in str(e):
            logger.warning(f"Job '{job_name}' not found.")
            return {"error": f"Job '{job_name}' not found."}
        logger.error(f"jenkins_get_build_parameters Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_build_parameters: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_recent_failed_builds(
    hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Internal logic for getting jobs whose LAST build failed within the specified recent period.
    Uses a single optimized API call for performance.

    Args:
        hours_ago: How many hours back to check for failed builds.

    Returns:
        A list of dictionaries for jobs whose last build failed recently, or an error dictionary.
    """
    logger.debug(
        f"jenkins_get_recent_failed_builds (OPTIMIZED) called for the last {hours_ago} hours"
    )

    # Check cache first
    cache_key = f"jenkins:recent_failed_builds:{hours_ago}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached

    # Get environment variables from client module
    from .client import get_jenkins_env_vars
    env_vars = get_jenkins_env_vars()
    jenkins_url = env_vars.get("JENKINS_URL")
    jenkins_user = env_vars.get("JENKINS_USER")
    jenkins_token = env_vars.get("JENKINS_TOKEN")

    if not jenkins_url or not jenkins_user or not jenkins_token:
        logger.error("Jenkins credentials (URL, USER, TOKEN) not configured.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }

    recent_failed_builds = []
    try:
        # Calculate the cutoff time in UTC
        now_utc = datetime.now(timezone.utc)
        cutoff_utc = now_utc - timedelta(hours=hours_ago)
        logger.debug(f"Checking for LAST builds failed since {cutoff_utc.isoformat()}")

        # --- Optimized API Call ---
        # Construct the API URL with the tree parameter
        # Request job name, url, and details of the lastBuild
        api_url = f"{jenkins_url.rstrip('/')}/api/json?tree=jobs[name,url,lastBuild[number,timestamp,result,url]]"
        logger.debug(f"Making optimized API call to: {api_url}")

        # Make the authenticated request (adjust timeout as needed)
        response = requests.get(
            api_url,
            auth=(jenkins_user, jenkins_token),
            timeout=60,  # Set a reasonable timeout for this single large request (e.g., 60 seconds)
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        # --- End Optimized API Call ---

        if "jobs" not in data:
            logger.warning("No 'jobs' key found in Jenkins API response.")
            return []  # Return empty list if no jobs data

        # Iterate through the jobs data obtained from the single API call
        for job_data in data.get("jobs", []):
            job_name = job_data.get("name")
            last_build_data = job_data.get("lastBuild")

            if not job_name:
                logger.warning("Found job data with no name, skipping.")
                continue

            logger.debug(f"Processing job: {job_name} from optimized response")

            if not last_build_data:
                logger.debug(
                    f"  Job '{job_name}' has no lastBuild information in the response."
                )
                continue

            # Extract last build details
            build_number = last_build_data.get("number")
            build_timestamp_ms = last_build_data.get("timestamp")
            status = last_build_data.get(
                "result"
            )  # 'result' usually holds FAILURE, SUCCESS, etc.
            build_url = last_build_data.get("url")

            if not build_timestamp_ms:
                logger.warning(
                    f"Last build for {job_name} (Num: {build_number}) missing timestamp data. Skipping."
                )
                continue

            # Convert timestamp and check time window
            build_timestamp_utc = datetime.fromtimestamp(
                build_timestamp_ms / 1000.0, tz=timezone.utc
            )

            if build_timestamp_utc >= cutoff_utc:
                logger.debug(
                    f"  Last build {job_name}#{build_number} is recent ({build_timestamp_utc.isoformat()}). Status: {status}"
                )
                # Check status
                if status == "FAILURE":
                    recent_failed_builds.append(
                        {
                            "job_name": job_name,
                            "build_number": build_number,
                            "status": status,
                            "timestamp_utc": build_timestamp_utc.isoformat(),
                            "url": build_url
                            or job_data.get("url", "") + str(build_number),  # Construct URL if needed
                        }
                    )
                    logger.info(f"Found recent failed LAST build: {job_name}#{build_number}")
                else:
                    logger.debug(
                        f"  Last build {job_name}#{build_number} was recent but status was not FAILURE (Status: {status})."
                    )
            else:
                logger.debug(
                    f"  Last build {job_name}#{build_number} ({build_timestamp_utc.isoformat()}) is older than cutoff ({cutoff_utc.isoformat()}). Skipping."
                )

        logger.debug(
            f"Finished processing optimized response. Found {len(recent_failed_builds)} jobs whose last build failed in the last {hours_ago} hours."
        )
        cache.set(cache_key, recent_failed_builds, ttl=300)  # Cache for 5 minutes
        return recent_failed_builds

    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error during optimized Jenkins API call: {e}", exc_info=True)
        return {"error": f"Timeout connecting to Jenkins API: {e}"}
    except requests.exceptions.ConnectionError as e:
        logger.error(
            f"Connection error during optimized Jenkins API call: {e}", exc_info=True
        )
        return {"error": f"Could not connect to Jenkins API: {e}"}
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error during optimized Jenkins API call: {e.response.status_code} - {e.response.text}",
            exc_info=True,
        )
        return {
            "error": f"Jenkins API HTTP Error: {e.response.status_code} - {e.response.reason}"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during optimized Jenkins API call: {e}", exc_info=True)
        return {"error": f"Jenkins API Request Error: {e}"}
    except Exception as e:  # Catch other potential errors (e.g., JSON parsing)
        logger.error(
            f"Unexpected error in jenkins_get_recent_failed_builds (optimized): {e}",
            exc_info=True,
        )
        return {"error": f"An unexpected error occurred: {e}"}