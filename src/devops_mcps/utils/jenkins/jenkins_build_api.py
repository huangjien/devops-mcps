"""Jenkins Build API functions."""

import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union

# Third-party imports
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build
from requests.exceptions import ConnectionError

# Internal imports
from ...cache import cache as _cache
from .jenkins_client import (
    j as _j,
    JENKINS_URL as _JENKINS_URL,
    JENKINS_USER as _JENKINS_USER,
    JENKINS_TOKEN as _JENKINS_TOKEN,
    LOG_LENGTH as _LOG_LENGTH
)
from .jenkins_converters import _to_dict as _original_to_dict

# Expose constants at module level for testing
JENKINS_URL = _JENKINS_URL
JENKINS_USER = _JENKINS_USER
JENKINS_TOKEN = _JENKINS_TOKEN
LOG_LENGTH = _LOG_LENGTH
j = _j
cache = _cache

def _get_jenkins_client():
    """Get the current Jenkins client, checking for patches in jenkins_api."""
    import sys
    jenkins_api_module = sys.modules.get('devops_mcps.utils.jenkins.jenkins_api')
    if jenkins_api_module and hasattr(jenkins_api_module, 'j'):
        return jenkins_api_module.j
    return _j

def _get_jenkins_constants():
    """Get the current Jenkins constants, checking for patches in jenkins_api."""
    import sys
    jenkins_api_module = sys.modules.get('devops_mcps.utils.jenkins.jenkins_api')
    if jenkins_api_module:
        return {
            'JENKINS_URL': getattr(jenkins_api_module, 'JENKINS_URL', _JENKINS_URL),
            'JENKINS_USER': getattr(jenkins_api_module, 'JENKINS_USER', _JENKINS_USER),
            'JENKINS_TOKEN': getattr(jenkins_api_module, 'JENKINS_TOKEN', _JENKINS_TOKEN),
            'LOG_LENGTH': getattr(jenkins_api_module, 'LOG_LENGTH', _LOG_LENGTH)
        }
    return {
        'JENKINS_URL': _JENKINS_URL,
        'JENKINS_USER': _JENKINS_USER,
        'JENKINS_TOKEN': _JENKINS_TOKEN,
        'LOG_LENGTH': _LOG_LENGTH
    }

def _get_to_dict():
    """Get the current _to_dict function, checking for patches in jenkins_api."""
    import sys
    jenkins_api_module = sys.modules.get('devops_mcps.utils.jenkins.jenkins_api')
    if jenkins_api_module and hasattr(jenkins_api_module, '_to_dict'):
        return jenkins_api_module._to_dict
    return _original_to_dict

def _get_cache():
    """Get the current cache object, checking for patches in jenkins_api."""
    import sys
    jenkins_api_module = sys.modules.get('devops_mcps.utils.jenkins.jenkins_api')
    if jenkins_api_module and hasattr(jenkins_api_module, 'cache'):
        return jenkins_api_module.cache
    return _cache

logger = logging.getLogger(__name__)


def jenkins_get_build_log(
    job_name: str, build_number: int, start: int = 0, lines: int = 50
) -> Union[str, Dict[str, str]]:
    """Internal logic for getting build log."""
    logger.debug(
        f"jenkins_get_build_log called with job_name: {job_name}, build_number: {build_number}, start: {start}, lines: {lines}"
    )

    # Check cache first
    cache_key = f"jenkins:build_log:{job_name}:{build_number}:{start}:{lines}"
    cache = _get_cache()
    cached_log = cache.get(cache_key)
    if cached_log:
        logger.debug(f"Returning cached build log for {cache_key}")
        return cached_log

    constants = _get_jenkins_constants()
    
    if not constants['JENKINS_URL'] or not constants['JENKINS_USER'] or not constants['JENKINS_TOKEN']:
        logger.error("Jenkins credentials not configured.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }

    try:
        # Use REST API to get console output
        if build_number > 0:
            console_url = f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"
        else:
            # Get last build number first
            job_url = f"{constants['JENKINS_URL']}/job/{job_name}/api/json"
            response = requests.get(
                job_url,
                auth=(constants['JENKINS_USER'], constants['JENKINS_TOKEN']),
                timeout=30,
            )
            response.raise_for_status()
            job_data = response.json()
            last_build = job_data.get('lastBuild')
            if not last_build:
                return {"error": f"No builds found for job {job_name}"}
            build_number = last_build.get('number')
            console_url = f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"

        # Get console output
        response = requests.get(
            console_url,
            auth=(constants['JENKINS_USER'], constants['JENKINS_TOKEN']),
            timeout=30,
        )
        response.raise_for_status()
        
        console_output = response.text
        if not console_output:
            logger.warning(f"No console output found for build {build_number}")
            return {"error": f"No console output found for build {build_number}"}

        # Extract the requested portion of the log
        log_lines = console_output.split("\n")
        end = min(start + lines, len(log_lines))
        log_portion = "\n".join(log_lines[start:end])

        logger.debug(f"Retrieved {len(log_lines)} total lines, returning lines {start} to {end}")
        cache.set(cache_key, log_portion, ttl=300)  # Cache for 5 minutes
        return log_portion

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"jenkins_get_build_log: Job '{job_name}' or build {build_number} not found.")
            return {"error": f"Job '{job_name}' or build {build_number} not found."}
        logger.error(f"jenkins_get_build_log HTTP error: {e}")
        return {"error": f"Jenkins API HTTP Error: {e.response.status_code}"}
    except ConnectionError as e:
        logger.error(f"jenkins_get_build_log connection error: {e}")
        return {"error": "Could not connect to Jenkins API"}
    except requests.exceptions.Timeout as e:
        logger.error(f"jenkins_get_build_log timeout error: {e}")
        return {"error": "Timeout connecting to Jenkins API"}
    except requests.exceptions.RequestException as e:
        logger.error(f"jenkins_get_build_log request error: {e}")
        return {"error": "Jenkins API Request Error"}
    except Exception as e:
        logger.error(f"jenkins_get_build_log error: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_build_parameters(
    job_name: str, build_number: int
) -> Union[Dict[str, Any], Dict[str, str]]:
    """Internal logic for getting build parameters.
    If build_number <= 0, returns the latest build parameters."""
    logger.debug(
        f"jenkins_get_build_parameters called for job: {job_name}, build: {build_number}"
    )

    # Check cache first
    cache_key = f"jenkins:build_parameters:{job_name}:{build_number}"
    cache = _get_cache()
    cached_params = cache.get(cache_key)
    if cached_params:
        logger.debug(f"Returning cached build parameters for {cache_key}")
        return cached_params

    constants = _get_jenkins_constants()
    
    if not constants['JENKINS_URL'] or not constants['JENKINS_USER'] or not constants['JENKINS_TOKEN']:
        logger.error("Jenkins credentials not configured.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }

    try:
        # Use REST API to get build information
        if build_number <= 0:
            # Get last build number first
            job_url = f"{constants['JENKINS_URL']}/job/{job_name}/api/json"
            response = requests.get(
                job_url,
                auth=(constants['JENKINS_USER'], constants['JENKINS_TOKEN']),
                timeout=30,
            )
            response.raise_for_status()
            job_data = response.json()
            last_build = job_data.get('lastBuild')
            if not last_build:
                return {"error": f"No builds found for job {job_name}"}
            build_number = last_build.get('number')

        # Get build information
        build_url = f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/api/json"
        response = requests.get(
            build_url,
            auth=(constants['JENKINS_USER'], constants['JENKINS_TOKEN']),
            timeout=30,
        )
        response.raise_for_status()
        build_info = response.json()

        # Extract parameters from build actions
        parameters = {}
        if "actions" in build_info:
            for action in build_info["actions"]:
                if "parameters" in action:
                    for param in action["parameters"]:
                        parameters[param["name"]] = param["value"]

        cache.set(cache_key, parameters, ttl=300)  # Cache for 5 minutes
        return parameters

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"jenkins_get_build_parameters: Job '{job_name}' or build {build_number} not found.")
            return {"error": f"Job '{job_name}' or build {build_number} not found."}
        logger.error(f"jenkins_get_build_parameters HTTP error: {e}")
        return {"error": f"Jenkins API HTTP Error: {e.response.status_code}"}
    except ConnectionError as e:
        logger.error(f"jenkins_get_build_parameters connection error: {e}")
        return {"error": "Could not connect to Jenkins API"}
    except requests.exceptions.Timeout as e:
        logger.error(f"jenkins_get_build_parameters timeout error: {e}")
        return {"error": "Timeout connecting to Jenkins API"}
    except requests.exceptions.RequestException as e:
        logger.error(f"jenkins_get_build_parameters request error: {e}")
        return {"error": "Jenkins API Request Error"}
    except Exception as e:
        logger.error(f"jenkins_get_build_parameters error: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_recent_failed_builds(
    hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """Internal logic for getting recent failed builds."""
    logger.debug(f"jenkins_get_recent_failed_builds called with hours_ago: {hours_ago}")

    # Check cache first
    cache_key = f"jenkins:recent_failed_builds:{hours_ago}"
    cache = _get_cache()
    cached_builds = cache.get(cache_key)
    if cached_builds:
        logger.debug(f"Returning cached recent failed builds for {cache_key}")
        return cached_builds

    constants = _get_jenkins_constants()
    
    if not constants['JENKINS_URL'] or not constants['JENKINS_USER'] or not constants['JENKINS_TOKEN']:
        logger.error("Jenkins credentials not configured.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }

    try:
        # Calculate the time threshold
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        time_threshold_ms = int(time_threshold.timestamp() * 1000)
        failed_builds = []

        # Get all jobs using REST API
        jobs_url = f"{constants['JENKINS_URL']}/api/json?tree=jobs[name,url,lastBuild[number,timestamp,result,url]]"
        response = requests.get(
            jobs_url,
            auth=(constants['JENKINS_USER'], constants['JENKINS_TOKEN']),
            timeout=30,
        )
        response.raise_for_status()
        
        jobs_data = response.json()
        jobs = jobs_data.get("jobs", [])
        logger.debug(f"Found {len(jobs)} jobs to check for recent failed builds.")

        for job in jobs:
            try:
                job_name = job.get("name")
                if not job_name:
                    continue
                    
                last_build = job.get("lastBuild")
                if not last_build:
                    continue

                # Check if the build is recent and failed
                build_timestamp = last_build.get("timestamp")
                build_result = last_build.get("result")
                
                if not build_timestamp:
                    continue
                    
                if build_timestamp >= time_threshold_ms and build_result in ["FAILURE", "UNSTABLE", "ABORTED"]:
                    build_number = last_build.get("number")
                    build_url = last_build.get("url")
                    
                    # If build URL is missing, construct it from job URL and build number
                    if not build_url:
                        job_url = job.get("url", "")
                        if job_url and build_number:
                            # Remove trailing slash from job URL if present
                            job_url = job_url.rstrip("/")
                            build_url = f"{job_url}{build_number}"
                    
                    # Convert timestamp to ISO format
                    build_time = datetime.fromtimestamp(build_timestamp / 1000, tz=timezone.utc)
                    
                    failed_builds.append(
                        {
                            "job_name": job_name,
                            "build_number": build_number,
                            "url": build_url,
                            "timestamp": build_time.isoformat(),
                            "status": build_result,
                            "result": build_result,
                            "duration": 0,
                            "description": "",
                            "causes": [],
                        }
                    )
            except Exception as job_error:
                logger.warning(
                    f"Error processing job {job.get('name', 'unknown')}: {job_error}"
                )
                continue

        logger.debug(f"Found {len(failed_builds)} recent failed builds.")
        cache.set(cache_key, failed_builds, ttl=300)  # Cache for 5 minutes
        return failed_builds

    except ConnectionError as e:
        logger.error(f"jenkins_get_recent_failed_builds connection error: {e}")
        return {"error": "Could not connect to Jenkins API"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"jenkins_get_recent_failed_builds HTTP error: {e}")
        return {"error": f"Jenkins API HTTP Error: {e.response.status_code}"}
    except requests.exceptions.Timeout as e:
        logger.error(f"jenkins_get_recent_failed_builds timeout error: {e}")
        return {"error": "Timeout connecting to Jenkins API"}
    except requests.exceptions.RequestException as e:
        logger.error(f"jenkins_get_recent_failed_builds request error: {e}")
        return {"error": "Jenkins API Request Error"}
    except Exception as e:
        logger.error(f"jenkins_get_recent_failed_builds error: {e}")
        return {"error": f"An unexpected error occurred: {e}"}