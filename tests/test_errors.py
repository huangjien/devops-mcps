"""Unit tests for errors.py."""

from devops_mcps.utils.errors import (
  ErrorCode,
  DevOpsMCPError,
  create_error_response,
  create_parameter_missing_error,
  create_authentication_error,
  create_configuration_error,
  create_api_error,
  wrap_exception,
)


class TestErrorCode:
  """Test the ErrorCode enum."""

  def test_error_code_values(self):
    """Test that all error codes have correct string values."""
    assert ErrorCode.AUTHENTICATION_FAILED.value == "AUTHENTICATION_FAILED"
    assert ErrorCode.AUTHENTICATION_MISSING.value == "AUTHENTICATION_MISSING"
    assert ErrorCode.AUTHENTICATION_INVALID.value == "AUTHENTICATION_INVALID"
    assert ErrorCode.CONFIGURATION_MISSING.value == "CONFIGURATION_MISSING"
    assert ErrorCode.CONFIGURATION_INVALID.value == "CONFIGURATION_INVALID"
    assert ErrorCode.PARAMETER_MISSING.value == "PARAMETER_MISSING"
    assert ErrorCode.PARAMETER_INVALID.value == "PARAMETER_INVALID"
    assert ErrorCode.NETWORK_ERROR.value == "NETWORK_ERROR"
    assert ErrorCode.API_ERROR.value == "API_ERROR"
    assert ErrorCode.API_RATE_LIMIT.value == "API_RATE_LIMIT"
    assert ErrorCode.API_TIMEOUT.value == "API_TIMEOUT"
    assert ErrorCode.RESOURCE_NOT_FOUND.value == "RESOURCE_NOT_FOUND"
    assert ErrorCode.RESOURCE_ACCESS_DENIED.value == "RESOURCE_ACCESS_DENIED"
    assert ErrorCode.UNKNOWN_ERROR.value == "UNKNOWN_ERROR"
    assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"


class TestDevOpsMCPError:
  """Test the DevOpsMCPError exception class."""

  def test_basic_initialization(self):
    """Test basic error initialization with code and message."""
    error = DevOpsMCPError(ErrorCode.AUTHENTICATION_FAILED, "Auth failed")
    assert error.code == ErrorCode.AUTHENTICATION_FAILED
    assert error.message == "Auth failed"
    assert error.details == {}
    assert error.original_exception is None

  def test_initialization_with_details(self):
    """Test error initialization with details."""
    details = {"user": "test", "attempt": 3}
    error = DevOpsMCPError(
      ErrorCode.PARAMETER_INVALID, "Invalid param", details=details
    )
    assert error.code == ErrorCode.PARAMETER_INVALID
    assert error.message == "Invalid param"
    assert error.details == details
    assert error.original_exception is None

  def test_initialization_with_original_exception(self):
    """Test error initialization with original exception."""
    original = ValueError("Original error")
    error = DevOpsMCPError(
      ErrorCode.INTERNAL_ERROR, "Wrapped error", original_exception=original
    )
    assert error.code == ErrorCode.INTERNAL_ERROR
    assert error.message == "Wrapped error"
    assert error.original_exception == original

  def test_to_dict_basic(self):
    """Test converting error to dictionary without details."""
    error = DevOpsMCPError(ErrorCode.API_ERROR, "API call failed")
    result = error.to_dict()
    assert result == {"error": "API call failed", "error_code": "API_ERROR"}

  def test_to_dict_with_details(self):
    """Test converting error to dictionary with details."""
    error = DevOpsMCPError(
      ErrorCode.RESOURCE_NOT_FOUND,
      "Resource not found",
      details={"resource_id": "123", "type": "job"},
    )
    result = error.to_dict()
    assert result == {
      "error": "Resource not found",
      "error_code": "RESOURCE_NOT_FOUND",
      "details": {"resource_id": "123", "type": "job"},
    }

  def test_str_representation(self):
    """Test string representation of error."""
    error = DevOpsMCPError(ErrorCode.NETWORK_ERROR, "Connection timeout")
    assert str(error) == "[NETWORK_ERROR] Connection timeout"

  def test_is_exception(self):
    """Test that DevOpsMCPError is an Exception subclass."""
    error = DevOpsMCPError(ErrorCode.UNKNOWN_ERROR, "Unknown")
    assert isinstance(error, Exception)
    assert isinstance(error, DevOpsMCPError)


class TestCreateErrorResponse:
  """Test the create_error_response function."""

  def test_basic_error_response(self):
    """Test creating basic error response."""
    result = create_error_response("Something went wrong")
    assert result == {"error": "Something went wrong", "error_code": "UNKNOWN_ERROR"}

  def test_error_response_with_code(self):
    """Test creating error response with specific error code."""
    result = create_error_response("Auth failed", code=ErrorCode.AUTHENTICATION_FAILED)
    assert result == {"error": "Auth failed", "error_code": "AUTHENTICATION_FAILED"}

  def test_error_response_with_details(self):
    """Test creating error response with details."""
    result = create_error_response(
      "Invalid input",
      code=ErrorCode.PARAMETER_INVALID,
      details={"field": "username", "value": ""},
    )
    assert result == {
      "error": "Invalid input",
      "error_code": "PARAMETER_INVALID",
      "details": {"field": "username", "value": ""},
    }

  def test_error_response_with_all_params(self):
    """Test creating error response with all parameters."""
    result = create_error_response(
      "API rate limit exceeded",
      code=ErrorCode.API_RATE_LIMIT,
      details={"limit": 100, "remaining": 0, "reset": 1234567890},
    )
    assert result == {
      "error": "API rate limit exceeded",
      "error_code": "API_RATE_LIMIT",
      "details": {"limit": 100, "remaining": 0, "reset": 1234567890},
    }


class TestCreateParameterMissingError:
  """Test the create_parameter_missing_error function."""

  def test_parameter_missing_error(self):
    """Test creating parameter missing error."""
    result = create_parameter_missing_error("username")
    assert result == {
      "error": "Parameter 'username' cannot be empty",
      "error_code": "PARAMETER_MISSING",
      "details": {"parameter": "username"},
    }

  def test_parameter_missing_error_with_complex_name(self):
    """Test creating parameter missing error with complex parameter name."""
    result = create_parameter_missing_error("api_token")
    assert result == {
      "error": "Parameter 'api_token' cannot be empty",
      "error_code": "PARAMETER_MISSING",
      "details": {"parameter": "api_token"},
    }


class TestCreateAuthenticationError:
  """Test the create_authentication_error function."""

  def test_authentication_error_default_reason(self):
    """Test creating authentication error with default reason."""
    result = create_authentication_error("GitHub")
    assert result == {
      "error": "GitHub Authentication failed",
      "error_code": "AUTHENTICATION_FAILED",
      "details": {"service": "GitHub", "reason": "Authentication failed"},
    }

  def test_authentication_error_custom_reason(self):
    """Test creating authentication error with custom reason."""
    result = create_authentication_error(
      "Jenkins", reason="Invalid credentials provided"
    )
    assert result == {
      "error": "Jenkins Invalid credentials provided",
      "error_code": "AUTHENTICATION_FAILED",
      "details": {"service": "Jenkins", "reason": "Invalid credentials provided"},
    }

  def test_authentication_error_with_token_expired(self):
    """Test creating authentication error with token expired."""
    result = create_authentication_error("Azure", reason="Token expired")
    assert result == {
      "error": "Azure Token expired",
      "error_code": "AUTHENTICATION_FAILED",
      "details": {"service": "Azure", "reason": "Token expired"},
    }


class TestCreateConfigurationError:
  """Test the create_configuration_error function."""

  def test_configuration_error_default_reason(self):
    """Test creating configuration error with default reason."""
    result = create_configuration_error("GITHUB_TOKEN")
    assert result == {
      "error": "GITHUB_TOKEN not configured",
      "error_code": "CONFIGURATION_MISSING",
      "details": {"config_key": "GITHUB_TOKEN", "reason": "not configured"},
    }

  def test_configuration_error_custom_reason(self):
    """Test creating configuration error with custom reason."""
    result = create_configuration_error("JENKINS_URL", reason="is not a valid URL")
    assert result == {
      "error": "JENKINS_URL is not a valid URL",
      "error_code": "CONFIGURATION_MISSING",
      "details": {"config_key": "JENKINS_URL", "reason": "is not a valid URL"},
    }

  def test_configuration_error_with_empty_value(self):
    """Test creating configuration error with empty value reason."""
    result = create_configuration_error("API_KEY", reason="is empty")
    assert result == {
      "error": "API_KEY is empty",
      "error_code": "CONFIGURATION_MISSING",
      "details": {"config_key": "API_KEY", "reason": "is empty"},
    }


class TestCreateApiError:
  """Test the create_api_error function."""

  def test_api_error_basic(self):
    """Test creating basic API error."""
    result = create_api_error("GitHub", "Repository not found")
    assert result == {
      "error": "GitHub API error: Repository not found",
      "error_code": "API_ERROR",
      "details": {"service": "GitHub", "reason": "Repository not found"},
    }

  def test_api_error_with_status_code(self):
    """Test creating API error with status code."""
    result = create_api_error("Jenkins", "Build not found", status_code=404)
    assert result == {
      "error": "Jenkins API error: Build not found",
      "error_code": "API_ERROR",
      "details": {
        "service": "Jenkins",
        "reason": "Build not found",
        "status_code": 404,
      },
    }

  def test_api_error_with_500_status(self):
    """Test creating API error with 500 status code."""
    result = create_api_error("Azure", "Internal server error", status_code=500)
    assert result == {
      "error": "Azure API error: Internal server error",
      "error_code": "API_ERROR",
      "details": {
        "service": "Azure",
        "reason": "Internal server error",
        "status_code": 500,
      },
    }


class TestWrapException:
  """Test the wrap_exception function."""

  def test_wrap_exception_default_context(self):
    """Test wrapping exception with default context."""
    exc = ValueError("Invalid value")
    result = wrap_exception(exc)
    assert result == {
      "error": "An error occurred in Unknown",
      "error_code": "INTERNAL_ERROR",
      "details": {"exception_type": "ValueError", "exception_message": "Invalid value"},
    }

  def test_wrap_exception_with_context(self):
    """Test wrapping exception with custom context."""
    exc = KeyError("missing_key")
    result = wrap_exception(exc, context="Data processing")
    assert result == {
      "error": "An error occurred in Data processing",
      "error_code": "INTERNAL_ERROR",
      "details": {"exception_type": "KeyError", "exception_message": "'missing_key'"},
    }

  def test_wrap_exception_with_complex_exception(self):
    """Test wrapping complex exception."""
    exc = RuntimeError("Database connection failed")
    result = wrap_exception(exc, context="Database query")
    assert result == {
      "error": "An error occurred in Database query",
      "error_code": "INTERNAL_ERROR",
      "details": {
        "exception_type": "RuntimeError",
        "exception_message": "Database connection failed",
      },
    }

  def test_wrap_exception_with_custom_exception(self):
    """Test wrapping custom exception."""

    class CustomError(Exception):
      pass

    exc = CustomError("Custom error message")
    result = wrap_exception(exc, context="Custom module")
    assert result == {
      "error": "An error occurred in Custom module",
      "error_code": "INTERNAL_ERROR",
      "details": {
        "exception_type": "CustomError",
        "exception_message": "Custom error message",
      },
    }

  def test_wrap_exception_with_empty_message(self):
    """Test wrapping exception with empty message."""
    exc = Exception()
    result = wrap_exception(exc, context="Test")
    assert result == {
      "error": "An error occurred in Test",
      "error_code": "INTERNAL_ERROR",
      "details": {"exception_type": "Exception", "exception_message": ""},
    }
