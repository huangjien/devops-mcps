"""Configuration validation module for DevOps MCP Server.

This module provides validation for all environment variables and configuration
settings to ensure early detection of configuration issues.
"""

import logging
import os
from typing import Optional, List, Tuple

from .utils.errors import (
  create_configuration_error,
)

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
  """Exception raised when configuration validation fails."""

  def __init__(self, message: str, errors: List[str]):
    self.message = message
    self.errors = errors
    super().__init__(self.message)


def validate_github_config() -> Tuple[bool, Optional[dict]]:
  """Validate GitHub configuration.

  Returns:
      Tuple of (is_valid, error_dict or None)
  """
  token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
  api_url = os.environ.get("GITHUB_API_URL")

  if not token:
    return False, create_configuration_error(
      "GITHUB_PERSONAL_ACCESS_TOKEN",
      "GitHub token is required for GitHub tools to function",
    )

  if token and not token.startswith("ghp_") and not token.startswith("github_pat_"):
    logger.warning(
      "GITHUB_PERSONAL_ACCESS_TOKEN may be invalid. "
      "Expected format: ghp_... or github_pat_..."
    )

  if api_url:
    if not api_url.startswith("http://") and not api_url.startswith("https://"):
      return False, create_configuration_error(
        "GITHUB_API_URL", "GITHUB_API_URL must start with http:// or https://"
      )

  return True, None


def validate_jenkins_config() -> Tuple[bool, Optional[dict]]:
  """Validate Jenkins configuration.

  Returns:
      Tuple of (is_valid, error_dict or None)
  """
  url = os.environ.get("JENKINS_URL")
  user = os.environ.get("JENKINS_USER")
  token = os.environ.get("JENKINS_TOKEN")
  log_length = os.environ.get("LOG_LENGTH")

  # Jenkins is optional - only validate if any config is provided
  has_config = bool(url or user or token)
  if has_config:
    # If any config is provided, all required fields must be present
    if not url:
      return False, create_configuration_error(
        "JENKINS_URL", "JENKINS_URL is required when using Jenkins tools"
      )
    if not user:
      return False, create_configuration_error(
        "JENKINS_USER", "JENKINS_USER is required when using Jenkins tools"
      )
    if not token:
      return False, create_configuration_error(
        "JENKINS_TOKEN", "JENKINS_TOKEN is required when using Jenkins tools"
      )

    if url and not url.startswith("http://") and not url.startswith("https://"):
      return False, create_configuration_error(
        "JENKINS_URL", "JENKINS_URL must start with http:// or https://"
      )

  # Validate LOG_LENGTH if provided
  if log_length:
    try:
      log_length_int = int(log_length)
      if log_length_int <= 0:
        return False, create_configuration_error(
          "LOG_LENGTH", "LOG_LENGTH must be a positive integer"
        )
      if log_length_int > 1048576:  # 1MB limit
        logger.warning(
          f"LOG_LENGTH is very large ({log_length_int} bytes). "
          "Consider using a smaller value."
        )
    except ValueError:
      return False, create_configuration_error(
        "LOG_LENGTH", "LOG_LENGTH must be a valid integer"
      )

  return True, None


def validate_artifactory_config() -> Tuple[bool, Optional[dict]]:
  """Validate Artifactory configuration.

  Returns:
      Tuple of (is_valid, error_dict or None)
  """
  url = os.environ.get("ARTIFACTORY_URL")
  identity_token = os.environ.get("ARTIFACTORY_IDENTITY_TOKEN")
  username = os.environ.get("ARTIFACTORY_USERNAME")
  password = os.environ.get("ARTIFACTORY_PASSWORD")

  # Artifactory is optional - only validate if any config is provided
  has_config = bool(url or identity_token or username or password)
  if has_config:
    if not url:
      return False, create_configuration_error(
        "ARTIFACTORY_URL", "ARTIFACTORY_URL is required when using Artifactory tools"
      )
    if not url.startswith("http://") and not url.startswith("https://"):
      return False, create_configuration_error(
        "ARTIFACTORY_URL", "ARTIFACTORY_URL must start with http:// or https://"
      )

    if not identity_token and not (username and password):
      return False, create_configuration_error(
        "ARTIFACTORY_AUTHENTICATION",
        "Either ARTIFACTORY_IDENTITY_TOKEN or "
        "(ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD) must be provided",
      )

  return True, None


def validate_azure_config() -> Tuple[bool, Optional[dict]]:
  """Validate Azure configuration.

  Returns:
      Tuple of (is_valid, error_dict or None)
  """
  # Azure uses DefaultAzureCredential which checks multiple sources
  # We can't validate all possibilities, but we can check common ones
  client_id = os.environ.get("AZURE_CLIENT_ID")
  client_secret = os.environ.get("AZURE_CLIENT_SECRET")
  tenant_id = os.environ.get("AZURE_TENANT_ID")

  if client_id or client_secret or tenant_id:
    # If any Azure env var is set, all should be set
    if not (client_id and client_secret and tenant_id):
      return False, create_configuration_error(
        "AZURE_CREDENTIALS",
        "When using service principal authentication, "
        "all of AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID must be provided",
      )

  return True, None


def validate_server_config() -> Tuple[bool, Optional[dict]]:
  """Validate server configuration.

  Returns:
      Tuple of (is_valid, error_dict or None)
  """
  port = os.environ.get("MCP_PORT", "3721")
  log_level = os.environ.get("LOG_LEVEL", "INFO")

  # Validate MCP_PORT
  try:
    port_int = int(port)
    if port_int < 1 or port_int > 65535:
      return False, create_configuration_error(
        "MCP_PORT", "MCP_PORT must be between 1 and 65535"
      )
  except ValueError:
    return False, create_configuration_error(
      "MCP_PORT", "MCP_PORT must be a valid integer"
    )

  # Validate LOG_LEVEL
  valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
  if log_level.upper() not in valid_levels:
    return False, create_configuration_error(
      "LOG_LEVEL", f"LOG_LEVEL must be one of: {', '.join(valid_levels)}"
    )

  # Validate PROMPTS_FILE if provided
  prompts_file = os.environ.get("PROMPTS_FILE")
  if prompts_file:
    if not os.path.exists(prompts_file):
      logger.warning(
        f"PROMPTS_FILE '{prompts_file}' does not exist. "
        "Dynamic prompts will not be loaded."
      )

  return True, None


def validate_all_config(strict: bool = False) -> Tuple[bool, List[str]]:
  """Validate all configuration.

  Args:
      strict: If True, fail on warnings. If False, only fail on errors.

  Returns:
      Tuple of (is_valid, list of error messages)
  """
  errors = []

  # Validate each configuration section
  is_valid, error = validate_github_config()
  if not is_valid:
    errors.append(error.get("error", "GitHub configuration error"))

  is_valid, error = validate_jenkins_config()
  if not is_valid:
    errors.append(error.get("error", "Jenkins configuration error"))

  is_valid, error = validate_artifactory_config()
  if not is_valid:
    errors.append(error.get("error", "Artifactory configuration error"))

  is_valid, error = validate_azure_config()
  if not is_valid:
    errors.append(error.get("error", "Azure configuration error"))

  is_valid, error = validate_server_config()
  if not is_valid:
    errors.append(error.get("error", "Server configuration error"))

  # Determine overall validity
  if strict and errors:
    return False, errors

  if errors:
    return False, errors

  return True, []


def print_validation_report(errors: List[str], warnings: List[str] = None) -> None:
  """Print validation report to logger.

  Args:
      errors: List of error messages
      warnings: Optional list of warning messages
  """
  if warnings:
    for warning in warnings:
      logger.warning(warning)

  if errors:
    logger.error("Configuration validation failed with the following errors:")
    for i, error in enumerate(errors, 1):
      logger.error(f"  {i}. {error}")
    logger.error("Please fix the configuration issues and restart the server.")
  else:
    logger.info("Configuration validation passed.")


# Export all public symbols
__all__ = [
  "ConfigValidationError",
  "validate_github_config",
  "validate_jenkins_config",
  "validate_artifactory_config",
  "validate_azure_config",
  "validate_server_config",
  "validate_all_config",
  "print_validation_report",
]
