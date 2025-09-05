"""Jenkins helper utilities for accessing client, constants, and other common functions."""

import logging
import sys
from typing import Dict

# Internal imports
from ...cache import cache as _cache
from .jenkins_client import (
  j as _j,
  JENKINS_URL as _JENKINS_URL,
  JENKINS_USER as _JENKINS_USER,
  JENKINS_TOKEN as _JENKINS_TOKEN,
  LOG_LENGTH as _LOG_LENGTH,
)
from .jenkins_converters import _to_dict as _original_to_dict

# Expose constants at module level for testing
JENKINS_URL = _JENKINS_URL
JENKINS_USER = _JENKINS_USER
JENKINS_TOKEN = _JENKINS_TOKEN
LOG_LENGTH = _LOG_LENGTH
j = _j
cache = _cache

logger = logging.getLogger(__name__)


def _get_jenkins_client():
  """Get the current Jenkins client, checking for patches in jenkins_api."""
  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "j"):
    return jenkins_api_module.j
  return _j


def _get_jenkins_constants():
  """Get the current Jenkins constants, checking for patches in jenkins_api."""
  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module:
    return {
      "JENKINS_URL": getattr(jenkins_api_module, "JENKINS_URL", _JENKINS_URL),
      "JENKINS_USER": getattr(jenkins_api_module, "JENKINS_USER", _JENKINS_USER),
      "JENKINS_TOKEN": getattr(jenkins_api_module, "JENKINS_TOKEN", _JENKINS_TOKEN),
      "LOG_LENGTH": getattr(jenkins_api_module, "LOG_LENGTH", _LOG_LENGTH),
    }
  return {
    "JENKINS_URL": _JENKINS_URL,
    "JENKINS_USER": _JENKINS_USER,
    "JENKINS_TOKEN": _JENKINS_TOKEN,
    "LOG_LENGTH": _LOG_LENGTH,
  }


def _get_to_dict():
  """Get the current _to_dict function, checking for patches in jenkins_api."""
  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "_to_dict"):
    return jenkins_api_module._to_dict
  return _original_to_dict


def _get_cache():
  """Get the current cache object, checking for patches in jenkins_api."""
  jenkins_api_module = sys.modules.get("devops_mcps.utils.jenkins.jenkins_api")
  if jenkins_api_module and hasattr(jenkins_api_module, "cache"):
    return jenkins_api_module.cache
  return _cache


def check_jenkins_credentials() -> Dict[str, str]:
  """Check if Jenkins credentials are configured and return error message if not."""
  constants = _get_jenkins_constants()

  if (
    not constants["JENKINS_URL"]
    or not constants["JENKINS_USER"]
    or not constants["JENKINS_TOKEN"]
  ):
    logger.error("Jenkins credentials not configured.")
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  return {}
