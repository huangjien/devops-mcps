"""Jenkins build parameters retrieval functionality."""

import logging
import requests
from typing import Dict, List, Union, Any

# Internal imports
from .jenkins_helpers import (
  _get_jenkins_constants,
  _get_cache,
  check_jenkins_credentials,
)

logger = logging.getLogger(__name__)


def jenkins_get_build_parameters(
  job_name: str, build_number: int = 0
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get build parameters for a specific Jenkins job and build number.

  Args:
      job_name: Name of the Jenkins job
      build_number: Build number to get parameters for (use 0 for latest build)

  Returns:
      List of parameter dictionaries or error dictionary
  """
  logger.debug(
    f"jenkins_get_build_parameters called with job_name: {job_name}, build_number: {build_number}"
  )

  # Check cache first
  cache_key = f"jenkins:build_parameters:{job_name}:{build_number}"
  cache = _get_cache()
  cached_parameters = cache.get(cache_key)
  if cached_parameters:
    logger.debug(f"Returning cached build parameters for {cache_key}")
    return cached_parameters

  # Check credentials
  credentials_error = check_jenkins_credentials()
  if credentials_error:
    cache.set(cache_key, credentials_error, ttl=300)  # Cache error for 5 minutes
    return credentials_error

  constants = _get_jenkins_constants()

  try:
    # Use REST API to get build parameters
    if build_number > 0:
      # Get parameters for a specific build
      build_url = f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/api/json"
    else:
      # Get parameters for the latest build
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
        error_dict = {"error": f"No builds found for job {job_name}"}
        cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
        return error_dict
      build_number = last_build.get("number")
      build_url = f"{constants['JENKINS_URL']}/job/{job_name}/{build_number}/api/json"

    # Get build data
    response = requests.get(
      build_url,
      auth=(constants["JENKINS_USER"], constants["JENKINS_TOKEN"]),
      timeout=30,
    )
    response.raise_for_status()
    build_data = response.json()

    # Extract parameters
    actions = build_data.get("actions", [])
    parameters = []
    for action in actions:
      if action.get("_class") == "hudson.model.ParametersAction":
        parameters = action.get("parameters", [])
        break

    # Convert parameters list to dictionary
    param_dict = {}
    for param in parameters:
      if "name" in param and "value" in param:
        param_dict[param["name"]] = param["value"]

    # Handle case when no parameters are found
    if not param_dict:
      logger.debug(f"No parameters found for build {build_number}")
      # Return empty dictionary for no parameters case
      param_dict = {}

    logger.debug(f"Retrieved {len(param_dict)} parameters for build {build_number}")
    cache.set(cache_key, param_dict, ttl=300)  # Cache for 5 minutes
    return param_dict

  except requests.exceptions.HTTPError as e:
    error_msg = ""
    if e.response.status_code == 404:
      error_msg = f"Job '{job_name}' or build {build_number} not found."
      logger.error(f"jenkins_get_build_parameters: {error_msg}")
    else:
      error_msg = f"Jenkins API HTTP Error: {e.response.status_code}"
      logger.error(f"jenkins_get_build_parameters HTTP error: {e}")

    error_dict = {"error": error_msg}
    cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
    return error_dict
  except requests.exceptions.ConnectionError as e:
    logger.error(f"jenkins_get_build_parameters connection error: {e}")
    error_dict = {"error": "Could not connect to Jenkins API"}
    cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
    return error_dict
  except requests.exceptions.Timeout as e:
    logger.error(f"jenkins_get_build_parameters timeout error: {e}")
    error_dict = {"error": "Timeout connecting to Jenkins API"}
    cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
    return error_dict
  except requests.exceptions.RequestException as e:
    logger.error(f"jenkins_get_build_parameters request error: {e}")
    error_dict = {"error": "Jenkins API Request Error"}
    cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
    return error_dict
  except Exception as e:
    logger.error(f"jenkins_get_build_parameters error: {e}")
    error_dict = {"error": f"An unexpected error occurred: {e}"}
    cache.set(cache_key, error_dict, ttl=300)  # Cache error for 5 minutes
    return error_dict
