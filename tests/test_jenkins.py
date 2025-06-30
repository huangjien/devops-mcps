import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.view import View
from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException

from devops_mcps.jenkins import (
  initialize_jenkins_client,
  _to_dict,
  jenkins_get_jobs,
  jenkins_get_build_log,
  jenkins_get_all_views,
  jenkins_get_build_parameters,
  jenkins_get_queue,
  jenkins_get_recent_failed_builds,
  set_jenkins_client_for_testing,
)


class TestInitializeJenkinsClient:
  """Test cases for initialize_jenkins_client function."""

  @patch("devops_mcps.jenkins.Jenkins")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_initialize_jenkins_client_success(self, mock_jenkins_class):
    """Test successful Jenkins client initialization."""
    mock_jenkins_instance = Mock()
    mock_jenkins_class.return_value = mock_jenkins_instance
    mock_jenkins_instance.get_master_data.return_value = {"test": "data"}

    # Reset global j
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = initialize_jenkins_client()

    assert result == mock_jenkins_instance
    assert devops_mcps.jenkins.j == mock_jenkins_instance

  @patch("devops_mcps.jenkins.Jenkins")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_initialize_jenkins_client_unexpected_error(self, mock_jenkins_class):
    """Test Jenkins client initialization with unexpected error."""
    mock_jenkins_class.side_effect = ValueError("Unexpected error")

    # Reset global j
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = initialize_jenkins_client()

    assert result is None
    assert devops_mcps.jenkins.j is None

  @patch("devops_mcps.jenkins.Jenkins")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_initialize_jenkins_client_jenkins_api_exception(self, mock_jenkins_class):
    """Test Jenkins client initialization with JenkinsAPIException."""
    mock_jenkins_class.side_effect = JenkinsAPIException("API error")

    # Reset global j
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = initialize_jenkins_client()

    assert result is None
    assert devops_mcps.jenkins.j is None

  @patch("devops_mcps.jenkins.Jenkins")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_initialize_jenkins_client_connection_error(self, mock_jenkins_class):
    """Test Jenkins client initialization with ConnectionError."""
    mock_jenkins_class.side_effect = ConnectionError("Connection failed")

    # Reset global j
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = initialize_jenkins_client()

    assert result is None
    assert devops_mcps.jenkins.j is None
    mock_jenkins_class.assert_called_once_with(
      "http://test-jenkins.com", username="testuser", password="testtoken"
    )
    # Note: get_master_data is not called when ConnectionError occurs during Jenkins() instantiation

  @patch("devops_mcps.jenkins.Jenkins")
  @patch.dict(
    os.environ,
    {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "testuser",
      "JENKINS_TOKEN": "testtoken",
    },
  )
  def test_initialize_jenkins_client_already_initialized(self, mock_jenkins_class):
    """Test that already initialized client is returned."""
    existing_client = Mock()
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = existing_client

    result = initialize_jenkins_client()

    assert result == existing_client
    mock_jenkins_class.assert_not_called()

  @patch.dict(os.environ, {}, clear=True)
  def test_initialize_jenkins_client_missing_credentials(self):
    """Test initialization with missing credentials."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = initialize_jenkins_client()

    assert result is None


class TestToDict:
  """Test cases for _to_dict helper function."""

  def test_to_dict_basic_types(self):
    """Test _to_dict with basic types."""
    assert _to_dict("string") == "string"
    assert _to_dict(123) == 123
    assert _to_dict(45.67) == 45.67
    assert _to_dict(True)
    assert _to_dict(None) is None

  def test_to_dict_list(self):
    """Test _to_dict with list."""
    test_list = ["a", 1, True, None]
    result = _to_dict(test_list)
    assert result == ["a", 1, True, None]

  def test_to_dict_dict(self):
    """Test _to_dict with dictionary."""
    test_dict = {"key1": "value1", "key2": 2}
    result = _to_dict(test_dict)
    assert result == {"key1": "value1", "key2": 2}

  def test_to_dict_job_object(self):
    """Test _to_dict with Job object."""
    mock_job = Mock()
    mock_job.__class__ = Job
    mock_job.name = "test-job"
    mock_job.baseurl = "http://jenkins.com/job/test-job"
    mock_job.is_enabled.return_value = True
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.return_value = 42
    mock_job.get_last_buildurl.return_value = "http://jenkins.com/job/test-job/42"

    result = _to_dict(mock_job)

    expected = {
      "name": "test-job",
      "url": "http://jenkins.com/job/test-job",
      "is_enabled": True,
      "is_queued": False,
      "in_queue": False,
      "last_build_number": 42,
      "last_build_url": "http://jenkins.com/job/test-job/42",
    }
    assert result == expected

  def test_to_dict_view_object(self):
    """Test _to_dict with View object."""
    mock_view = Mock()
    mock_view.__class__ = View
    mock_view.name = "test-view"
    mock_view.baseurl = "http://jenkins.com/view/test-view"
    mock_view.get_description.return_value = "Test view description"

    result = _to_dict(mock_view)

    expected = {
      "name": "test-view",
      "url": "http://jenkins.com/view/test-view",
      "description": "Test view description",
    }
    assert result == expected

  def test_to_dict_unknown_object(self):
    """Test _to_dict with unknown object type."""

    class UnknownObject:
      def __str__(self):
        return "unknown object"

    unknown_obj = UnknownObject()
    result = _to_dict(unknown_obj)
    assert result == "unknown object"

  def test_to_dict_object_with_str_error(self):
    """Test _to_dict with object that raises error on str()."""

    class ErrorObject:
      def __str__(self):
        raise Exception("str error")

    error_obj = ErrorObject()
    result = _to_dict(error_obj)
    assert "Error serializing object of type ErrorObject" in result


class TestJenkinsGetJobs:
  """Test cases for jenkins_get_jobs function."""

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_jobs_jenkins_api_exception(self, mock_cache):
    """Test jenkins_get_jobs with JenkinsAPIException."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.keys.side_effect = JenkinsAPIException("API error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_jobs()

    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_jobs_unexpected_exception(self, mock_cache):
    """Test jenkins_get_jobs with unexpected exception."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.keys.side_effect = ValueError("Unexpected error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_jobs()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_jobs_cached_result(self, mock_cache):
    """Test jenkins_get_jobs returns cached result."""
    cached_data = [{"name": "cached-job"}]
    mock_cache.get.return_value = cached_data

    result = jenkins_get_jobs()

    assert result == cached_data
    mock_cache.get.assert_called_once_with("jenkins:jobs:all")

  def test_jenkins_get_jobs_no_client(self):
    """Test jenkins_get_jobs with no Jenkins client."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    with patch("devops_mcps.jenkins.cache") as mock_cache:
      mock_cache.get.return_value = None

      result = jenkins_get_jobs()

      assert "error" in result
      assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_jobs_success(self, mock_cache):
    """Test successful jenkins_get_jobs."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.keys.return_value = ["job1", "job2"]

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    with patch("devops_mcps.jenkins._to_dict", side_effect=lambda x: f"dict_{x}"):
      result = jenkins_get_jobs()

      assert result == ["dict_job1", "dict_job2"]
      mock_cache.set.assert_called_once_with(
        "jenkins:jobs:all", ["dict_job1", "dict_job2"], ttl=300
      )


class TestJenkinsGetBuildLog:
  """Test cases for jenkins_get_build_log function."""

  def test_jenkins_get_build_log_no_client(self):
    """Test jenkins_get_build_log with no Jenkins client."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = jenkins_get_build_log("test-job", 1)

    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_log_cached_result(self, mock_cache):
    """Test jenkins_get_build_log returns cached result."""
    cached_log = "cached build log"
    mock_cache.get.return_value = cached_log

    mock_jenkins = Mock()
    mock_job = Mock()
    mock_job.get_last_buildnumber.return_value = 5
    mock_jenkins.get_job.return_value = mock_job

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_log("test-job", 5)

    assert result == cached_log

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_log_success(self, mock_cache):
    """Test successful jenkins_get_build_log."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_job = Mock()
    mock_build = Mock()
    mock_build.get_console.return_value = (
      "This is a long build log that should be truncated"
    )

    mock_job.get_last_buildnumber.return_value = 5
    mock_job.get_build.return_value = mock_build
    mock_jenkins.get_job.return_value = mock_job

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_log("test-job", 0)  # Use 0 to get latest

    assert isinstance(result, str)
    mock_cache.set.assert_called_once()

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_log_jenkins_api_exception(self, mock_cache):
    """Test jenkins_get_build_log with JenkinsAPIException."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_job.side_effect = JenkinsAPIException("Job not found")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_log("test-job", 1)

    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_log_unexpected_exception(self, mock_cache):
    """Test jenkins_get_build_log with unexpected exception."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_job.side_effect = ValueError("Unexpected error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_log("test-job", 1)

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_log_build_not_found(self, mock_cache):
    """Test jenkins_get_build_log with build not found."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_job = Mock()
    mock_job.get_build.return_value = None
    mock_jenkins.get_job.return_value = mock_job

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_log("test-job", 999)

    assert "error" in result
    assert "Build #999 not found" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_parameters_jenkins_api_exception(self, mock_cache):
    """Test jenkins_get_build_parameters with JenkinsAPIException."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_job.side_effect = JenkinsAPIException("Job access error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_parameters("test-job", 1)

    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_parameters_unexpected_exception(self, mock_cache):
    """Test jenkins_get_build_parameters with unexpected exception."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_job.side_effect = ValueError("Unexpected error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_parameters("test-job", 1)

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


class TestJenkinsGetAllViews:
  """Test cases for jenkins_get_all_views function."""

  def test_jenkins_get_all_views_no_client(self):
    """Test jenkins_get_all_views with no Jenkins client."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    with patch("devops_mcps.jenkins.cache") as mock_cache:
      mock_cache.get.return_value = None

      result = jenkins_get_all_views()

      assert "error" in result
      assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_all_views_success(self, mock_cache):
    """Test successful jenkins_get_all_views."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.views.keys.return_value = ["view1", "view2"]

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    with patch("devops_mcps.jenkins._to_dict", side_effect=lambda x: f"dict_{x}"):
      result = jenkins_get_all_views()

      assert result == ["dict_view1", "dict_view2"]
      mock_cache.set.assert_called_once_with(
        "jenkins:views:all", ["dict_view1", "dict_view2"], ttl=600
      )

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_all_views_jenkins_api_exception(self, mock_cache):
    """Test jenkins_get_all_views with JenkinsAPIException."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.views.keys.side_effect = JenkinsAPIException("Views access error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_all_views()

    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_all_views_unexpected_exception(self, mock_cache):
    """Test jenkins_get_all_views with unexpected exception."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.views.keys.side_effect = ValueError("Unexpected error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_all_views()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


class TestJenkinsGetBuildParameters:
  """Test cases for jenkins_get_build_parameters function."""

  def test_jenkins_get_build_parameters_no_client(self):
    """Test jenkins_get_build_parameters with no Jenkins client."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    result = jenkins_get_build_parameters("test-job", 1)

    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_parameters_success(self, mock_cache):
    """Test successful jenkins_get_build_parameters."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_job = Mock()
    mock_build = Mock()
    mock_build.get_params.return_value = {"param1": "value1", "param2": "value2"}

    mock_job.get_build.return_value = mock_build
    mock_jenkins.get_job.return_value = mock_job

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_parameters("test-job", 1)

    assert result == {"param1": "value1", "param2": "value2"}
    mock_cache.set.assert_called_once()

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_build_parameters_build_not_found(self, mock_cache):
    """Test jenkins_get_build_parameters with build not found."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_job = Mock()
    mock_job.get_build.return_value = None
    mock_jenkins.get_job.return_value = mock_job

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_build_parameters("test-job", 999)

    assert "error" in result
    assert "Build #999 not found" in result["error"]


class TestJenkinsGetQueue:
  """Test cases for jenkins_get_queue function."""

  def test_jenkins_get_queue_no_client(self):
    """Test jenkins_get_queue with no Jenkins client."""
    import devops_mcps.jenkins

    devops_mcps.jenkins.j = None

    with patch("devops_mcps.jenkins.cache") as mock_cache:
      mock_cache.get.return_value = None

      result = jenkins_get_queue()

      assert "error" in result
      assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_queue_success(self, mock_cache):
    """Test successful jenkins_get_queue."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_queue = Mock()
    mock_queue.get_queue_items.return_value = ["item1", "item2"]
    mock_jenkins.get_queue.return_value = mock_queue

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    with patch("devops_mcps.jenkins._to_dict", return_value=["item1", "item2"]):
      result = jenkins_get_queue()

      assert result == {"queue_items": ["item1", "item2"]}
      mock_cache.set.assert_called_once()

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_queue_jenkins_api_exception(self, mock_cache):
    """Test jenkins_get_queue with JenkinsAPIException."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_queue.side_effect = JenkinsAPIException("Queue access error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_queue()

    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_queue_unexpected_exception(self, mock_cache):
    """Test jenkins_get_queue with unexpected exception."""
    mock_cache.get.return_value = None

    mock_jenkins = Mock()
    mock_jenkins.get_queue.side_effect = ValueError("Unexpected error")

    import devops_mcps.jenkins

    devops_mcps.jenkins.j = mock_jenkins

    result = jenkins_get_queue()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


class TestJenkinsGetRecentFailedBuilds:
  """Test cases for jenkins_get_recent_failed_builds function."""

  @patch("devops_mcps.jenkins.cache")
  def test_jenkins_get_recent_failed_builds_cached_result(self, mock_cache):
    """Test jenkins_get_recent_failed_builds returns cached result."""
    cached_data = [{"job_name": "cached-job"}]
    mock_cache.get.return_value = cached_data

    result = jenkins_get_recent_failed_builds(8)

    assert result == cached_data
    mock_cache.get.assert_called_once_with("jenkins:recent_failed_builds:8")

  @patch("devops_mcps.jenkins.JENKINS_URL", None)
  @patch("devops_mcps.jenkins.JENKINS_USER", None)
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", None)
  def test_jenkins_get_recent_failed_builds_no_credentials(self):
    """Test jenkins_get_recent_failed_builds with no credentials."""
    with patch("devops_mcps.jenkins.cache") as mock_cache:
      mock_cache.get.return_value = None

      result = jenkins_get_recent_failed_builds(8)

      assert "error" in result
      assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.jenkins.requests.get")
  @patch("devops_mcps.jenkins.cache")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_jenkins_get_recent_failed_builds_connection_error(
    self, mock_cache, mock_requests_get
  ):
    """Test jenkins_get_recent_failed_builds with ConnectionError."""
    mock_cache.get.return_value = None
    mock_requests_get.side_effect = ConnectionError("Connection failed")

    result = jenkins_get_recent_failed_builds(8)

    assert "error" in result
    assert "Could not connect to Jenkins API" in result["error"]

  @patch("devops_mcps.jenkins.requests.get")
  @patch("devops_mcps.jenkins.cache")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_jenkins_get_recent_failed_builds_http_error(
    self, mock_cache, mock_requests_get
  ):
    """Test jenkins_get_recent_failed_builds with HTTPError."""
    mock_cache.get.return_value = None

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.reason = "Not Found"
    mock_response.text = "Page not found"

    http_error = HTTPError(response=mock_response)
    http_error.response = mock_response
    mock_requests_get.side_effect = http_error

    result = jenkins_get_recent_failed_builds(8)

    assert "error" in result
    assert "Jenkins API HTTP Error" in result["error"]
    assert "404" in result["error"]

  @patch("devops_mcps.jenkins.requests.get")
  @patch("devops_mcps.jenkins.cache")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_jenkins_get_recent_failed_builds_request_exception(
    self, mock_cache, mock_requests_get
  ):
    """Test jenkins_get_recent_failed_builds with RequestException."""
    mock_cache.get.return_value = None
    mock_requests_get.side_effect = RequestException("Request failed")

    result = jenkins_get_recent_failed_builds(8)

    assert "error" in result
    assert "Jenkins API Request Error" in result["error"]

  @patch("devops_mcps.jenkins.requests.get")
  @patch("devops_mcps.jenkins.cache")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_jenkins_get_recent_failed_builds_success(
    self, mock_cache, mock_requests_get
  ):
    """Test successful jenkins_get_recent_failed_builds."""
    mock_cache.get.return_value = None

    # Mock the API response
    now = datetime.now(timezone.utc)
    recent_timestamp = int((now - timedelta(hours=1)).timestamp() * 1000)

    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {
          "name": "failed-job",
          "url": "http://jenkins.com/job/failed-job",
          "lastBuild": {
            "number": 42,
            "timestamp": recent_timestamp,
            "result": "FAILURE",
            "url": "http://jenkins.com/job/failed-job/42",
          },
        },
        {
          "name": "success-job",
          "url": "http://jenkins.com/job/success-job",
          "lastBuild": {
            "number": 43,
            "timestamp": recent_timestamp,
            "result": "SUCCESS",
            "url": "http://jenkins.com/job/success-job/43",
          },
        },
      ]
    }
    mock_requests_get.return_value = mock_response

    result = jenkins_get_recent_failed_builds(8)

    assert len(result) == 1
    assert result[0]["job_name"] == "failed-job"
    assert result[0]["status"] == "FAILURE"
    mock_cache.set.assert_called_once()

  @patch("devops_mcps.jenkins.requests.get")
  @patch("devops_mcps.jenkins.cache")
  @patch("devops_mcps.jenkins.JENKINS_URL", "http://test-jenkins.com")
  @patch("devops_mcps.jenkins.JENKINS_USER", "testuser")
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
  def test_jenkins_get_recent_failed_builds_timeout(
    self, mock_cache, mock_requests_get
  ):
    """Test jenkins_get_recent_failed_builds with timeout error."""
    mock_cache.get.return_value = None
    mock_requests_get.side_effect = Timeout("Request timeout")

    result = jenkins_get_recent_failed_builds(8)

    assert "error" in result
    assert "Timeout connecting to Jenkins API" in result["error"]


class TestSetJenkinsClientForTesting:
  """Test cases for set_jenkins_client_for_testing function."""

  def test_set_jenkins_client_for_testing(self):
    """Test set_jenkins_client_for_testing function."""
    mock_client = Mock()

    set_jenkins_client_for_testing(mock_client)

    import devops_mcps.jenkins

    assert devops_mcps.jenkins.j == mock_client

  def test_set_jenkins_client_for_testing_none(self):
    """Test set_jenkins_client_for_testing with None."""
    set_jenkins_client_for_testing(None)

    import devops_mcps.jenkins

    assert devops_mcps.jenkins.j is None
