"""Tests for jenkins_parameters module."""

from unittest.mock import Mock, patch
import requests
from src.devops_mcps.utils.jenkins.jenkins_parameters import (
  jenkins_get_build_parameters,
)


class TestJenkinsBuildParameters:
  """Test class for jenkins_get_build_parameters function."""

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_cached_result(self, mock_get_cache):
    """Test that cached results are returned when available."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = {"param1": "value1", "param2": "value2"}
    mock_get_cache.return_value = mock_cache

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"param1": "value1", "param2": "value2"}
    mock_cache.get.assert_called_once_with("jenkins:build_parameters:test-job:123")

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_no_credentials(
    self, mock_get_cache, mock_check_credentials
  ):
    """Test error handling when Jenkins credentials are missing."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = {
      "error": "Jenkins credentials not configured"
    }

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Jenkins credentials not configured"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Jenkins credentials not configured"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_specific_build_success(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test successful retrieval of parameters for a specific build."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.json.return_value = {
      "actions": [
        {
          "_class": "hudson.model.ParametersAction",
          "parameters": [
            {"name": "BRANCH", "value": "main"},
            {"name": "VERSION", "value": "1.0.0"},
          ],
        }
      ]
    }
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"BRANCH": "main", "VERSION": "1.0.0"}
    mock_requests_get.assert_called_once_with(
      "http://jenkins.example.com/job/test-job/123/api/json",
      auth=("user", "token"),
      timeout=30,
    )
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"BRANCH": "main", "VERSION": "1.0.0"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_latest_build_success(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test successful retrieval of parameters for the latest build."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    # Mock job response (first call)
    job_response = Mock()
    job_response.json.return_value = {"lastBuild": {"number": 456}}

    # Mock build response (second call)
    build_response = Mock()
    build_response.json.return_value = {
      "actions": [
        {
          "_class": "hudson.model.ParametersAction",
          "parameters": [{"name": "ENV", "value": "production"}],
        }
      ]
    }

    mock_requests_get.side_effect = [job_response, build_response]

    # Execute
    result = jenkins_get_build_parameters("test-job", 0)

    # Assert
    assert result == {"ENV": "production"}
    assert mock_requests_get.call_count == 2
    mock_requests_get.assert_any_call(
      "http://jenkins.example.com/job/test-job/api/json",
      auth=("user", "token"),
      timeout=30,
    )
    mock_requests_get.assert_any_call(
      "http://jenkins.example.com/job/test-job/456/api/json",
      auth=("user", "token"),
      timeout=30,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_no_builds_found(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling when no builds are found for a job."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.json.return_value = {"lastBuild": None}
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_parameters("test-job", 0)

    # Assert
    assert result == {"error": "No builds found for job test-job"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:0",
      {"error": "No builds found for job test-job"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_no_parameters(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling when build has no parameters."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.json.return_value = {"actions": [{"_class": "some.other.Action"}]}
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123", {}, ttl=300
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_http_404_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for HTTP 404 errors."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.status_code = 404
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_requests_get.side_effect = http_error

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Job 'test-job' or build 123 not found."}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Job 'test-job' or build 123 not found."},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_http_500_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for HTTP 500 errors."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.status_code = 500
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_requests_get.side_effect = http_error

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Jenkins API HTTP Error: 500"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Jenkins API HTTP Error: 500"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_connection_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for connection errors."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_requests_get.side_effect = requests.exceptions.ConnectionError(
      "Connection failed"
    )

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Could not connect to Jenkins API"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Could not connect to Jenkins API"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_timeout_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for timeout errors."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_requests_get.side_effect = requests.exceptions.Timeout("Request timed out")

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Timeout connecting to Jenkins API"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Timeout connecting to Jenkins API"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_request_exception(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for general request exceptions."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_requests_get.side_effect = requests.exceptions.RequestException(
      "Request failed"
    )

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "Jenkins API Request Error"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "Jenkins API Request Error"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_unexpected_exception(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test error handling for unexpected exceptions."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_requests_get.side_effect = ValueError("Unexpected error")

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert
    assert result == {"error": "An unexpected error occurred: Unexpected error"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"error": "An unexpected error occurred: Unexpected error"},
      ttl=300,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_parameters._get_cache")
  def test_jenkins_get_build_parameters_malformed_parameters(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of malformed parameter data."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    mock_response = Mock()
    mock_response.json.return_value = {
      "actions": [
        {
          "_class": "hudson.model.ParametersAction",
          "parameters": [
            {"name": "VALID_PARAM", "value": "valid_value"},
            {"name": "MISSING_VALUE"},  # Missing value
            {"value": "missing_name"},  # Missing name
            {"name": "ANOTHER_VALID", "value": "another_value"},
          ],
        }
      ]
    }
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_parameters("test-job", 123)

    # Assert - only valid parameters should be included
    assert result == {"VALID_PARAM": "valid_value", "ANOTHER_VALID": "another_value"}
    mock_cache.set.assert_called_once_with(
      "jenkins:build_parameters:test-job:123",
      {"VALID_PARAM": "valid_value", "ANOTHER_VALID": "another_value"},
      ttl=300,
    )
