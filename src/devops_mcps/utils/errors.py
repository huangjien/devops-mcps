"""Common error handling utilities for DevOps MCP Server.

This module provides consistent error response formats and custom exceptions
to ensure uniform error handling across all modules.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

ErrorResponse = Dict[str, Any]


class ErrorCode(Enum):
  """Enumeration of common error codes."""

  # Authentication and authorization errors
  AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
  AUTHENTICATION_MISSING = "AUTHENTICATION_MISSING"
  AUTHENTICATION_INVALID = "AUTHENTICATION_INVALID"

  # Configuration errors
  CONFIGURATION_MISSING = "CONFIGURATION_MISSING"
  CONFIGURATION_INVALID = "CONFIGURATION_INVALID"

  # Parameter validation errors
  PARAMETER_MISSING = "PARAMETER_MISSING"
  PARAMETER_INVALID = "PARAMETER_INVALID"

  # Network and API errors
  NETWORK_ERROR = "NETWORK_ERROR"
  API_ERROR = "API_ERROR"
  API_RATE_LIMIT = "API_RATE_LIMIT"
  API_TIMEOUT = "API_TIMEOUT"

  # Resource errors
  RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
  RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"

  # General errors
  UNKNOWN_ERROR = "UNKNOWN_ERROR"
  INTERNAL_ERROR = "INTERNAL_ERROR"


class DevOpsMCPError(Exception):
  """Base exception class for DevOps MCP Server errors.

  Attributes:
      code: Error code from ErrorCode enum
      message: Human-readable error message
      details: Additional error details (optional)
      original_exception: The original exception that caused this error (optional)
  """

  def __init__(
    self,
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    original_exception: Optional[Exception] = None,
  ):
    self.code = code
    self.message = message
    self.details = details or {}
    self.original_exception = original_exception
    super().__init__(self.message)

  def to_dict(self) -> Dict[str, Any]:
    """Convert error to dictionary format.

    Returns:
        Dictionary representation of the error.
    """
    result: ErrorResponse = {
      "error": self.message,
      "error_code": self.code.value,
    }
    if self.details:
      result["details"] = self.details
    return result

  def __str__(self) -> str:
    return f"[{self.code.value}] {self.message}"


def create_error_response(
  message: str,
  code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
  details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
  """Create a standardized error response dictionary.

  Args:
      message: Human-readable error message
      code: Error code from ErrorCode enum
      details: Additional error details (optional)

  Returns:
      Dictionary with error information
  """
  result: ErrorResponse = {
    "error": message,
    "error_code": code.value,
  }
  if details:
    result["details"] = details
  logger.debug(f"Error response created: {code.value} - {message}")
  return result


def create_parameter_missing_error(param_name: str) -> ErrorResponse:
  """Create an error response for missing parameter.

  Args:
      param_name: Name of the missing parameter

  Returns:
      Dictionary with error information
  """
  return create_error_response(
    message=f"Parameter '{param_name}' cannot be empty",
    code=ErrorCode.PARAMETER_MISSING,
    details={"parameter": param_name},
  )


def create_authentication_error(
  service: str,
  reason: str = "Authentication failed",
) -> ErrorResponse:
  """Create an error response for authentication failure.

  Args:
      service: Name of the service (e.g., "GitHub", "Jenkins")
      reason: Reason for authentication failure

  Returns:
      Dictionary with error information
  """
  return create_error_response(
    message=f"{service} {reason}",
    code=ErrorCode.AUTHENTICATION_FAILED,
    details={"service": service, "reason": reason},
  )


def create_configuration_error(
  config_key: str,
  reason: str = "not configured",
) -> ErrorResponse:
  """Create an error response for missing configuration.

  Args:
      config_key: Name of the missing configuration key
      reason: Reason for configuration error

  Returns:
      Dictionary with error information
  """
  return create_error_response(
    message=f"{config_key} {reason}",
    code=ErrorCode.CONFIGURATION_MISSING,
    details={"config_key": config_key, "reason": reason},
  )


def create_api_error(
  service: str,
  reason: str,
  status_code: Optional[int] = None,
) -> ErrorResponse:
  """Create an error response for API errors.

  Args:
      service: Name of the service (e.g., "GitHub", "Jenkins")
      reason: Reason for API error
      status_code: HTTP status code (if available)

  Returns:
      Dictionary with error information
  """
  details: Dict[str, Any] = {"service": service, "reason": reason}
  if status_code:
    details["status_code"] = status_code
  return create_error_response(
    message=f"{service} API error: {reason}",
    code=ErrorCode.API_ERROR,
    details=details,
  )


def wrap_exception(
  exception: Exception,
  context: str = "Unknown",
) -> ErrorResponse:
  """Wrap an exception in a standardized error response.

  Args:
      exception: The exception to wrap
      context: Context where the exception occurred

  Returns:
      Dictionary with error information
  """
  logger.error(f"Exception in {context}: {type(exception).__name__}: {exception}")
  return create_error_response(
    message=f"An error occurred in {context}",
    code=ErrorCode.INTERNAL_ERROR,
    details={
      "exception_type": type(exception).__name__,
      "exception_message": str(exception),
    },
  )


# Export all public symbols
__all__ = [
  "ErrorCode",
  "DevOpsMCPError",
  "create_error_response",
  "create_parameter_missing_error",
  "create_authentication_error",
  "create_configuration_error",
  "create_api_error",
  "wrap_exception",
]
