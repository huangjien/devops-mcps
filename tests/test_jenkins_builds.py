"""Tests for Jenkins build information functionality."""

from unittest.mock import Mock, patch
import requests
from datetime import datetime
from src.devops_mcps.utils.jenkins.jenkins_builds import (
  jenkins_get_recent_failed_builds,
)


class TestJenkinsRecentFailedBuilds:
  """Test class for Jenkins recent failed builds functionality."""

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_cached_result(self, mock_get_cache):
    """Test that cached results are returned when available."""
    # Setup
    mock_cache = Mock()
    cached_builds = [
      {
        "job_name": "test-job",
        "build_number": 123,
        "timestamp": 1640995200000,
        "timestamp_iso": "2022-01-01T00:00:00",
        "result": "FAILURE",
        "build_url": "http://jenkins.example.com/job/test-job/123/",
      }
    ]
    mock_cache.get.return_value = cached_builds
    mock_get_cache.return_value = mock_cache

    # Execute
    result = jenkins_get_recent_failed_builds(24)

    # Verify
    assert result == cached_builds
    mock_cache.get.assert_called_once_with("jenkins:recent_failed_builds:24")

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_no_credentials(
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "Jenkins credentials not configured"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.datetime")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_success(
    self,
    mock_get_cache,
    mock_check_credentials,
    mock_get_constants,
    mock_requests_get,
    mock_datetime,
  ):
    """Test successful retrieval of recent failed builds."""
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

    # Mock datetime for time threshold calculation
    mock_now = datetime(2022, 1, 2, 12, 0, 0)
    mock_datetime.now.return_value = mock_now
    mock_datetime.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)

    # Mock API response with failed builds
    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {
          "name": "failed-job",
          "url": "http://jenkins.example.com/job/failed-job/",
          "lastBuild": {
            "number": 123,
            "timestamp": 1641124800000,  # Recent timestamp (within 24 hours)
            "result": "FAILURE",
            "url": "http://jenkins.example.com/job/failed-job/123/",
          },
        },
        {
          "name": "success-job",
          "url": "http://jenkins.example.com/job/success-job/",
          "lastBuild": {"number": 456, "timestamp": 1641124800000, "result": "SUCCESS"},
        },
        {
          "name": "old-failed-job",
          "url": "http://jenkins.example.com/job/old-failed-job/",
          "lastBuild": {
            "number": 789,
            "timestamp": 1640908800000,  # Old timestamp (more than 24 hours ago)
            "result": "FAILURE",
          },
        },
      ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_recent_failed_builds(24)

    # Verify
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["job_name"] == "failed-job"
    assert result[0]["build_number"] == 123
    assert result[0]["result"] == "FAILURE"
    assert result[0]["build_url"] == "http://jenkins.example.com/job/failed-job/123/"
    mock_cache.set.assert_called_once_with(
      "jenkins:recent_failed_builds:24", result, ttl=300
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.datetime")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_no_last_build(
    self,
    mock_get_cache,
    mock_check_credentials,
    mock_get_constants,
    mock_requests_get,
    mock_datetime,
  ):
    """Test handling of jobs with no last build."""
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

    mock_now = datetime(2022, 1, 2, 12, 0, 0)
    mock_datetime.now.return_value = mock_now

    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {
          "name": "no-builds-job",
          "url": "http://jenkins.example.com/job/no-builds-job/",
          "lastBuild": None,
        }
      ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_recent_failed_builds(24)

    # Verify
    assert isinstance(result, list)
    assert len(result) == 0

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.datetime")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_missing_build_url(
    self,
    mock_get_cache,
    mock_check_credentials,
    mock_get_constants,
    mock_requests_get,
    mock_datetime,
  ):
    """Test handling of builds with missing URL that gets constructed."""
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

    mock_now = datetime(2022, 1, 2, 12, 0, 0)
    mock_datetime.now.return_value = mock_now
    mock_datetime.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)

    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {
          "name": "failed-job-no-url",
          "url": "http://jenkins.example.com/job/failed-job-no-url/",
          "lastBuild": {
            "number": 123,
            "timestamp": 1641124800000,
            "result": "FAILURE",
            # No 'url' field in lastBuild
          },
        }
      ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_recent_failed_builds(24)

    # Verify
    assert isinstance(result, list)
    assert len(result) == 1
    assert (
      result[0]["build_url"] == "http://jenkins.example.com/job/failed-job-no-url/123/"
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_connection_error(
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "Could not connect to Jenkins API"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_http_error(
    self, mock_get_cache, mock_check_credentials, mock_get_constants, mock_requests_get
  ):
    """Test handling of HTTP error."""
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "Jenkins API HTTP Error: 500"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_timeout_error(
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "Timeout connecting to Jenkins API"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_request_exception(
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "Jenkins API Request Error"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_unexpected_exception(
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
    result = jenkins_get_recent_failed_builds()

    # Verify
    assert result == {"error": "An unexpected error occurred: Unexpected error"}

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.datetime")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_empty_jobs(
    self,
    mock_get_cache,
    mock_check_credentials,
    mock_get_constants,
    mock_requests_get,
    mock_datetime,
  ):
    """Test handling when no jobs are returned from Jenkins."""
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

    mock_now = datetime(2022, 1, 2, 12, 0, 0)
    mock_datetime.now.return_value = mock_now

    mock_response = Mock()
    mock_response.json.return_value = {"jobs": []}
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_recent_failed_builds(12)

    # Verify
    assert isinstance(result, list)
    assert len(result) == 0
    mock_cache.set.assert_called_once_with(
      "jenkins:recent_failed_builds:12", [], ttl=300
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.datetime")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.requests.get")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds.check_jenkins_credentials")
  @patch("src.devops_mcps.utils.jenkins.jenkins_builds._get_cache")
  def test_jenkins_get_recent_failed_builds_missing_timestamp(
    self,
    mock_get_cache,
    mock_check_credentials,
    mock_get_constants,
    mock_requests_get,
    mock_datetime,
  ):
    """Test handling of builds with missing timestamp (defaults to 0)."""
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

    mock_now = datetime(2022, 1, 2, 12, 0, 0)
    mock_datetime.now.return_value = mock_now

    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {
          "name": "failed-job-no-timestamp",
          "url": "http://jenkins.example.com/job/failed-job-no-timestamp/",
          "lastBuild": {
            "number": 123,
            # No 'timestamp' field
            "result": "FAILURE",
          },
        }
      ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Execute
    result = jenkins_get_recent_failed_builds(24)

    # Verify - should not include this build since timestamp defaults to 0 (very old)
    assert isinstance(result, list)
    assert len(result) == 0
