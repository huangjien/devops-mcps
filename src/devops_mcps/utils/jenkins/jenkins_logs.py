"""Jenkins build log retrieval functionality."""

import logging
import requests
from typing import Dict, Union

# Internal imports
from .jenkins_helpers import (
  _get_jenkins_constants,
  _get_cache,
  check_jenkins_credentials,
)

logger = logging.getLogger(__name__)


def jenkins_get_build_log(
  job_name: str, build_number: int, start: int = 0, lines: int = 50
) -> Union[str, Dict[str, str]]:
  """Get build log for a specific Jenkins job and build number.

  Args:
      job_name: Name of the Jenkins job
      build_number: Build number to get logs for (use 0 or negative for latest build)
      start: Starting line number (0-indexed)
      lines: Number of lines to retrieve

  Returns:
      String containing the log content or error dictionary
  """
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

  # Check credentials
  credentials_error = check_jenkins_credentials()
  if credentials_error:
    return credentials_error

  constants = _get_jenkins_constants()

  try:
    # Use REST API to get console output
    if build_number > 0:
      console_url = (
        f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"
      )
    else:
      # Get last build number first
      job_url = f"{constants['JENKINS_URL']}/job/{job_name}/api/json"
      response = requests.get(
        job_url,
        auth=(constants["JENKINS_USER"], constants["JENKINS_TOKEN"]),
        timeout=30,
      )
      response.raise_for_status()
      job_data = response.json()
      last_build = job_data.get("lastBuild")
      if not last_build:
        return {"error": f"No builds found for job {job_name}"}
      build_number = last_build.get("number")
      console_url = (
        f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"
      )

    # Get console output
    response = requests.get(
      console_url,
      auth=(constants["JENKINS_USER"], constants["JENKINS_TOKEN"]),
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

    logger.debug(
      f"Retrieved {len(log_lines)} total lines, returning lines {start} to {end}"
    )
    cache.set(cache_key, log_portion, ttl=300)  # Cache for 5 minutes
    return log_portion

  except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
      logger.error(
        f"jenkins_get_build_log: Job '{job_name}' or build {build_number} not found."
      )
      return {"error": f"Job '{job_name}' or build {build_number} not found."}
    logger.error(f"jenkins_get_build_log HTTP error: {e}")
    return {"error": f"Jenkins API HTTP Error: {e.response.status_code}"}
  except requests.exceptions.ConnectionError as e:
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
