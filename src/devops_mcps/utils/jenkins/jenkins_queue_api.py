"""Jenkins Queue API functions."""

import logging
from typing import Dict, Any, Union

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


def jenkins_get_queue() -> Union[Dict[str, Any], Dict[str, str]]:
  """Get the current Jenkins queue information."""
  logger.debug("jenkins_get_queue called")

  # Check cache first
  cache_key = "jenkins:queue:current"
  cache = _get_cache()
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  j = _get_jenkins_client()
  constants = _get_jenkins_constants()
  to_dict = _get_to_dict()

  if not j:
    logger.error("jenkins_get_queue: Jenkins client not initialized.")
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
    queue_info = j.get_queue().get_queue_items()  # Example: get items
    logger.debug(f"Retrieved queue info: {queue_info}")
    # Note: jenkinsapi might return specific objects here, adjust _to_dict or processing as needed
    result = {"queue_items": to_dict(queue_info)}  # Wrap in a dict for clarity
    cache.set(
      cache_key, result, ttl=60
    )  # Cache for 1 minute (queue changes frequently)
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_queue Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {str(e)}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_queue: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
