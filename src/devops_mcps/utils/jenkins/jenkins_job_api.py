"""Jenkins Job API functions."""

import logging
from typing import List, Dict, Any, Union

# Third-party imports
from jenkinsapi.jenkins import JenkinsAPIException

# Internal imports
from ...cache import cache as _cache
from .jenkins_client import (
  j as _j,
  JENKINS_URL as _JENKINS_URL,
  JENKINS_USER as _JENKINS_USER,
  JENKINS_TOKEN as _JENKINS_TOKEN,
)
from .jenkins_converters import _to_dict as _original_to_dict

# Expose constants at module level for testing
JENKINS_URL = _JENKINS_URL
JENKINS_USER = _JENKINS_USER
JENKINS_TOKEN = _JENKINS_TOKEN
j = _j
cache = _cache


# Function to get current values (allows for test patching)
def _get_jenkins_client():
  """Get the current Jenkins client, checking for patches in jenkins_api."""
  import sys

  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "j"):
    return jenkins_api_module.j
  return _j


def _get_jenkins_constants():
  """Get current Jenkins constants, checking for patches in jenkins_api."""
  import sys

  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module:
    return {
      "JENKINS_URL": getattr(jenkins_api_module, "JENKINS_URL", _JENKINS_URL),
      "JENKINS_USER": getattr(jenkins_api_module, "JENKINS_USER", _JENKINS_USER),
      "JENKINS_TOKEN": getattr(jenkins_api_module, "JENKINS_TOKEN", _JENKINS_TOKEN),
    }
  return {
    "JENKINS_URL": _JENKINS_URL,
    "JENKINS_USER": _JENKINS_USER,
    "JENKINS_TOKEN": _JENKINS_TOKEN,
  }


def _get_to_dict():
  """Get the current _to_dict function, checking for patches in jenkins_api."""
  import sys

  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "_to_dict"):
    return jenkins_api_module._to_dict
  return _original_to_dict


def _get_cache():
  """Get the current cache object, checking for patches in jenkins_api."""
  import sys

  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "cache"):
    return jenkins_api_module.cache
  return _cache


logger = logging.getLogger(__name__)


def jenkins_get_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for getting all jobs."""
  logger.debug("jenkins_get_jobs called")

  # Check cache first
  cache_key = "jenkins:jobs:all"
  cache = _get_cache()
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  j = _get_jenkins_client()
  constants = _get_jenkins_constants()

  if not j:
    logger.error("jenkins_get_jobs: Jenkins client not initialized.")
    if (
      not constants["JENKINS_URL"]
      or not constants["JENKINS_USER"]
      or not constants["JENKINS_TOKEN"]
    ):
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  try:
    jobs = j.values()
    logger.debug(f"Found {len(jobs)} jobs.")
    to_dict_func = _get_to_dict()
    result = [to_dict_func(job) for job in jobs]
    cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
