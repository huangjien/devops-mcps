"""Tests for Jenkins build log functionality."""

from unittest.mock import Mock, patch
import requests
from src.devops_mcps.utils.jenkins.jenkins_logs import jenkins_get_build_log


class TestJenkinsBuildLogs:
  """Test class for Jenkins build log functionality."""

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_cached_result(self, mock_get_cache):
    """Test that cached results are returned when available."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = "cached log content"
    mock_get_cache.return_value = mock_cache

    # Execute
    result = jenkins_get_build_log("test-job", 123, 0, 50)

    # Verify
    assert result == "cached log content"
    mock_cache.get.assert_called_once_with("jenkins:build_log:test-job:123:0:50")

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_no_credentials(
    self, mock_get_cache, mock_check_credentials
  ):
    """Test handling when Jenkins credentials are not available."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = {
      "error": "Jenkins credentials not configured"
    }

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "Jenkins credentials not configured"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_specific_build_success(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test successful retrieval of build log for specific build number."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_log("test-job", 123, 1, 2)

    # Verify
    assert result == "Line 2\nLine 3"
    mock_requests_get.assert_called_once_with(
      "http://jenkins.example.com/job/test-job/123/consoleText",
      auth=("testuser", "testtoken"),
      timeout=30,
    )
    mock_cache.set.assert_called_once_with(
      "jenkins:build_log:test-job:123:1:2", "Line 2\nLine 3", ttl=300
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_latest_build_success(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test successful retrieval of build log for latest build (build_number <= 0)."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    # Mock job API response
    job_response = Mock()
    job_response.json.return_value = {"lastBuild": {"number": 456}}
    job_response.raise_for_status.return_value = None

    # Mock console output response
    console_response = Mock()
    console_response.text = "Latest build log content\nSecond line"
    console_response.raise_for_status.return_value = None

    mock_requests_get.side_effect = [job_response, console_response]

    # Execute
    result = jenkins_get_build_log("test-job", 0, 0, 50)

    # Verify
    assert result == "Latest build log content\nSecond line"
    assert mock_requests_get.call_count == 2
    mock_requests_get.assert_any_call(
      "http://jenkins.example.com/job/test-job/api/json",
      auth=("testuser", "testtoken"),
      timeout=30,
    )
    mock_requests_get.assert_any_call(
      "http://jenkins.example.com/job/test-job/456/consoleText",
      auth=("testuser", "testtoken"),
      timeout=30,
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_no_builds_found(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling when no builds are found for the job."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.json.return_value = {"lastBuild": None}
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_log("test-job", -1)

    # Verify
    assert result == {"error": "No builds found for job test-job"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_empty_console_output(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling when console output is empty."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.text = ""
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "No console output found for build 123"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_http_404_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of HTTP 404 error (job or build not found)."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.status_code = 404
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_requests_get.side_effect = http_error

    # Execute
    result = jenkins_get_build_log("nonexistent-job", 999)

    # Verify
    assert result == {"error": "Job 'nonexistent-job' or build 999 not found."}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_http_500_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of HTTP 500 error (server error)."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.status_code = 500
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_requests_get.side_effect = http_error

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "Jenkins API HTTP Error: 500"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_connection_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of connection error."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_requests_get.side_effect = requests.exceptions.ConnectionError(
      "Connection failed"
    )

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "Could not connect to Jenkins API"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_timeout_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of timeout error."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_requests_get.side_effect = requests.exceptions.Timeout("Request timed out")

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "Timeout connecting to Jenkins API"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_request_exception(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of general request exception."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_requests_get.side_effect = requests.exceptions.RequestException(
      "Request failed"
    )

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "Jenkins API Request Error"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_unexpected_exception(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of unexpected exception."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_requests_get.side_effect = ValueError("Unexpected error")

    # Execute
    result = jenkins_get_build_log("test-job", 123)

    # Verify
    assert result == {"error": "An unexpected error occurred: Unexpected error"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_logs._get_cache")
  def test_jenkins_get_build_log_line_range_handling(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test proper handling of start and lines parameters for log extraction."""
    # Setup
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_check_credentials.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    }

    mock_response = Mock()
    mock_response.text = "Line 0\nLine 1\nLine 2\nLine 3\nLine 4\nLine 5"
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute - request lines beyond available content
    result = jenkins_get_build_log("test-job", 123, 3, 10)

    # Verify - should return from line 3 to end
    assert result == "Line 3\nLine 4\nLine 5"
