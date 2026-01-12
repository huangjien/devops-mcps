"""Jenkins View API functions."""

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


def _get_jenkins_client():
  """Get Jenkins client, checking for patched version in jenkins_api."""
  try:
    from . import jenkins_api

    return getattr(jenkins_api, "j", _j)
  except (ImportError, AttributeError):
    return _j


def _get_jenkins_constants():
  """Get Jenkins constants, checking for patched versions in jenkins_api."""
  try:
    from . import jenkins_api

    return {
      "JENKINS_URL": getattr(jenkins_api, "JENKINS_URL", _JENKINS_URL),
      "JENKINS_USER": getattr(jenkins_api, "JENKINS_USER", _JENKINS_USER),
      "JENKINS_TOKEN": getattr(jenkins_api, "JENKINS_TOKEN", _JENKINS_TOKEN),
    }
  except (ImportError, AttributeError):
    return {
      "JENKINS_URL": _JENKINS_URL,
      "JENKINS_USER": _JENKINS_USER,
      "JENKINS_TOKEN": _JENKINS_TOKEN,
    }


def _get_to_dict():
  """Get _to_dict function, checking for patched version in jenkins_api."""
  try:
    from . import jenkins_api

    return getattr(jenkins_api, "_to_dict", _original_to_dict)
  except (ImportError, AttributeError):
    return _original_to_dict


def _get_cache():
  """Get cache object, checking for patched version in jenkins_api."""
  try:
    from . import jenkins_api

    return getattr(jenkins_api, "cache", _cache)
  except (ImportError, AttributeError):
    return _cache


logger = logging.getLogger(__name__)


def jenkins_get_all_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all the views from the Jenkins."""
  logger.debug("jenkins_get_all_views called")

  # Check cache first
  cache_key = "jenkins:views:all"
  cache = _get_cache()
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  j = _get_jenkins_client()
  constants = _get_jenkins_constants()
  to_dict = _get_to_dict()

  if not j:
    logger.error("jenkins_get_all_views: Jenkins client not initialized.")
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
    views = j.views.keys()
    logger.debug(f"Found {len(views)} views.")
    result = [to_dict(view) for view in views]  # modified to use .values()
    cache.set(cache_key, result, ttl=600)  # Cache for 10 minutes
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_all_views Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_all_views: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
