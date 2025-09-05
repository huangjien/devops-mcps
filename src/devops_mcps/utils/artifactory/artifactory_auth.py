"""Artifactory authentication and configuration utilities.

This module provides authentication and configuration validation functions
for Artifactory API operations.
"""

import os
import logging
from typing import Dict, Union, Tuple, Optional

# Initialize logger
logger = logging.getLogger(__name__)


def get_auth() -> Optional[Union[Dict[str, str], Tuple[str, str]]]:
  """Returns the appropriate authentication method for Artifactory API calls.

  Returns:
      Dict with Authorization header for token auth, tuple for basic auth, or None if no auth configured
  """
  # Get the values directly from os.environ to ensure we get the latest values
  identity_token = os.environ.get("ARTIFACTORY_IDENTITY_TOKEN", "")
  username = os.environ.get("ARTIFACTORY_USERNAME", "")
  password = os.environ.get("ARTIFACTORY_PASSWORD", "")

  if identity_token:
    return {"Authorization": f"Bearer {identity_token}"}
  elif username and password:
    return (username, password)
  return None


def validate_artifactory_config() -> Union[bool, Dict[str, str]]:
  """Validates that the required Artifactory configuration is available.

  Returns:
      True if configuration is valid, error dictionary otherwise
  """
  # Get the values directly from os.environ to ensure we get the latest values
  url = os.environ.get("ARTIFACTORY_URL", "")
  identity_token = os.environ.get("ARTIFACTORY_IDENTITY_TOKEN", "")
  username = os.environ.get("ARTIFACTORY_USERNAME", "")
  password = os.environ.get("ARTIFACTORY_PASSWORD", "")

  if not url:
    logger.error("Artifactory URL not configured")
    return {
      "error": "Artifactory URL not configured. Please set the ARTIFACTORY_URL environment variable."
    }

  if not (identity_token or (username and password)):
    logger.error("Artifactory authentication not configured")
    return {
      "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
    }

  return True
