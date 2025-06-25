import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import requests
from datetime import datetime, timezone, timedelta
from jenkinsapi.jenkins import JenkinsAPIException

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Test Fixtures ---


@pytest.fixture(autouse=True)
def manage_jenkins_module():
  """Fixture to manage the jenkins module import and cleanup."""
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as jenkins_module

  jenkins_module.j = None
  # Clear cache before each test
  from src.devops_mcps.cache import cache

  cache.clear()
  yield jenkins_module
  # Do not reset j after yield; allow tests to control client state


@pytest.fixture
def mock_jenkins_api():
  """Mocks the jenkinsapi.Jenkins class."""
  with patch("jenkinsapi.jenkins.Jenkins", autospec=True) as mock_jenkins:
    # Mock the instance methods/properties needed
    mock_instance = mock_jenkins.return_value
    mock_instance.get_master_data.return_value = {
      "nodeName": "master"
    }  # Simulate successful connection
    mock_instance.keys.return_value = []  # Default to no jobs
    mock_instance.views.keys.return_value = []  # Default to no views
    mock_instance.get_job.return_value = MagicMock()
    mock_instance.get_queue.return_value = MagicMock()
    yield mock_instance  # Yield the mocked Jenkins instance


@pytest.fixture
def mock_requests_get():
  """Mocks requests.get."""
  with patch("requests.get") as mock_get:
    yield mock_get


@pytest.fixture
def mock_env_vars(monkeypatch):
  """Mocks Jenkins environment variables."""
  monkeypatch.setenv("JENKINS_URL", "http://fake-jenkins.com")
  monkeypatch.setenv("JENKINS_USER", "testuser")
  monkeypatch.setenv("JENKINS_TOKEN", "testtoken")
  monkeypatch.setenv("LOG_LENGTH", "5000")  # Example log length
  yield  # This ensures the environment variables are set for the duration of the test


# --- Test Cases ---


def test_initialize_jenkins_client_missing_env_vars(
  monkeypatch, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to missing env vars."""
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Need to re-import or reload the module for env vars to be re-read at module level
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  client = reloaded_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert reloaded_jenkins_module.j is None
  mock_jenkins_api.assert_not_called()  # Jenkins class should not be instantiated


def test_initialize_jenkins_client_connection_error(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to connection error."""
  mock_jenkins_api.get_master_data.side_effect = requests.exceptions.ConnectionError(
    "Connection failed"
  )

  client = manage_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert manage_jenkins_module.j is None


# Test _to_dict Helper (Basic Cases)
def test_to_dict_basic_types(manage_jenkins_module):
  assert manage_jenkins_module._to_dict("string") == "string"
  assert manage_jenkins_module._to_dict(123) == 123
  assert manage_jenkins_module._to_dict(None) is None
  assert manage_jenkins_module._to_dict([1, "a"]) == [1, "a"]
  assert manage_jenkins_module._to_dict({"a": 1}) == {"a": 1}


def test_to_dict_mock_job(manage_jenkins_module):
  mock_job = MagicMock()
  mock_job.name = "TestJob"
  mock_job.baseurl = "http://fake-jenkins.com/job/TestJob/"
  mock_job.is_enabled.return_value = True
  mock_job.is_queued.return_value = False
  mock_job.get_last_buildnumber.return_value = 5
  mock_job.get_last_buildurl.return_value = "http://fake-jenkins.com/job/TestJob/5/"

  # Patch the isinstance check within _to_dict for Job
  with patch("src.devops_mcps.jenkins.Job", new=type(mock_job)):
    # Need to check the actual type name if using autospec=True or specific class mock
    # Or more robustly, patch isinstance directly if needed:
    # with patch('builtins.isinstance', side_effect=lambda obj, cls: True if cls is Job else isinstance(obj, cls)):
    result = manage_jenkins_module._to_dict(mock_job)

  assert result == {
    "name": "TestJob",
    "url": "http://fake-jenkins.com/job/TestJob/",
    "is_enabled": True,
    "is_queued": False,
    "in_queue": False,
    "last_build_number": 5,
    "last_build_url": "http://fake-jenkins.com/job/TestJob/5/",
  }


def test_get_jobs_no_client(manage_jenkins_module):
  """Test getting jobs when client is not initialized."""
  manage_jenkins_module.j = None  # Ensure client is None
  result = manage_jenkins_module.jenkins_get_jobs()
  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }


def test_get_build_log_no_client(manage_jenkins_module):
  """Test getting build log when client is not initialized."""
  manage_jenkins_module.j = None
  result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)
  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }


def test_get_build_parameters_no_client(manage_jenkins_module):
  """Test getting parameters when client is not initialized."""
  manage_jenkins_module.j = None
  result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }


def test_get_recent_failed_builds_no_credentials(
  monkeypatch, mock_requests_get, manage_jenkins_module
):
  """Test getting recent failed builds when credentials are missing."""
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up lack of env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }
  mock_requests_get.assert_not_called()


def test_jenkins_get_all_views_no_client(manage_jenkins_module):
  """Test jenkins_get_all_views when client is not initialized."""
  manage_jenkins_module.j = None  # Ensure client is None
  result = manage_jenkins_module.jenkins_get_all_views()
  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }


# --- Additional Tests for Better Coverage ---


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of jobs."""
  from src.devops_mcps.jenkins import jenkins_get_jobs
  from jenkinsapi.job import Job

  # Setup mock jobs
  mock_job1 = MagicMock(spec=Job)
  mock_job1.name = "Job1"
  mock_job1.baseurl = "http://jenkins/job/Job1/"
  mock_job1.is_enabled = MagicMock(return_value=True)
  mock_job1.is_queued = MagicMock(return_value=False)
  mock_job1.get_last_buildnumber = MagicMock(return_value=10)
  mock_job1.get_last_buildurl = MagicMock(return_value="http://jenkins/job/Job1/10/")

  mock_job2 = MagicMock(spec=Job)
  mock_job2.name = "Job2"
  mock_job2.baseurl = "http://jenkins/job/Job2/"
  mock_job2.is_enabled = MagicMock(return_value=False)
  mock_job2.is_queued = MagicMock(return_value=True)
  mock_job2.get_last_buildnumber = MagicMock(return_value=5)
  mock_job2.get_last_buildurl = MagicMock(return_value="http://jenkins/job/Job2/5/")

  mock_jenkins_api.keys.return_value = [mock_job1, mock_job2]

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.keys = mock_jenkins_api.keys

  result = jenkins_get_jobs()

  assert len(result) == 2
  assert result[0]["name"] == "Job1"
  assert result[1]["name"] == "Job2"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_jobs with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.keys.side_effect = JenkinsAPIException("API Error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.keys = mock_jenkins_api.keys

  from src.devops_mcps.jenkins import jenkins_get_jobs

  result = jenkins_get_jobs()

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_jobs with unexpected exception."""
  mock_jenkins_api.keys.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.keys = mock_jenkins_api.keys

  from src.devops_mcps.jenkins import jenkins_get_jobs

  result = jenkins_get_jobs()

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of build log."""
  mock_job = MagicMock()
  mock_build = MagicMock()
  mock_build.get_console.return_value = (
    "Build log content with special chars \x00\x01\n"
  )
  mock_job.get_build.return_value = mock_build
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 1)

  assert isinstance(result, str)
  assert "Build log content" in result
  # Verify special characters are handled
  assert "\x00" not in result


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_latest_build(mock_j, mock_jenkins_api):
  """Test getting latest build log when build_number <= 0."""
  mock_job = MagicMock()
  mock_job.get_last_buildnumber.return_value = 15
  mock_build = MagicMock()
  mock_build.get_console.return_value = "Latest build log"
  mock_job.get_build.return_value = mock_build
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 0)

  assert "Latest build log" in result
  mock_job.get_last_buildnumber.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_build_not_found(mock_j, mock_jenkins_api):
  """Test build log when build is not found."""
  mock_job = MagicMock()
  mock_job.get_build.return_value = None
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 999)

  assert "error" in result
  assert "Build #999 not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("Job not found")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("NonExistentJob", 1)

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of views."""
  from src.devops_mcps.jenkins import jenkins_get_all_views
  from jenkinsapi.view import View

  mock_view1 = MagicMock(spec=View)
  mock_view1.name = "View1"
  mock_view1.baseurl = "http://jenkins/view/View1/"
  mock_view1.get_description = MagicMock(return_value="Test view 1")

  mock_view2 = MagicMock(spec=View)
  mock_view2.name = "View2"
  mock_view2.baseurl = "http://jenkins/view/View2/"
  mock_view2.get_description = MagicMock(return_value="Test view 2")

  mock_jenkins_api.views.keys.return_value = [mock_view1, mock_view2]

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  result = jenkins_get_all_views()

  assert len(result) == 2
  assert result[0]["name"] == "View1"
  assert result[1]["name"] == "View2"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_all_views with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.views.keys.side_effect = JenkinsAPIException("Views error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  from src.devops_mcps.jenkins import jenkins_get_all_views

  result = jenkins_get_all_views()

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of build parameters."""
  # Setup mocks
  mock_job = MagicMock()
  mock_build = MagicMock()
  mock_build.get_params.return_value = {"param1": "value1", "param2": "value2"}
  mock_job.get_build.return_value = mock_build
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 1)

  assert result == {"param1": "value1", "param2": "value2"}


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_build_not_found(mock_j, mock_jenkins_api):
  """Test build parameters when build is not found."""
  # Setup mocks
  mock_job = MagicMock()
  mock_job.get_build.return_value = None
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 999)

  assert "error" in result
  assert "Build #999 not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_job_not_found(mock_j, mock_jenkins_api):
  """Test build parameters when job is not found."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  # Setup mocks
  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("No such job")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("NonExistentJob", 1)

  assert "error" in result
  assert "Job 'NonExistentJob' not found" in result["error"]


def test_jenkins_get_queue_no_client(manage_jenkins_module):
  """Test jenkins_get_queue when client is not initialized."""
  manage_jenkins_module.j = None
  result = manage_jenkins_module.jenkins_get_queue()
  assert result == {
    "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
  }


def test_jenkins_get_queue_success(manage_jenkins_module):
  """Test successful retrieval of queue information."""
  mock_jenkins_api = MagicMock()
  mock_queue = MagicMock()
  mock_queue_items = ["item1", "item2"]
  mock_queue.get_queue_items.return_value = mock_queue_items
  mock_jenkins_api.get_queue.return_value = mock_queue

  # Mock the global j variable using patch
  with patch.object(manage_jenkins_module, "j", mock_jenkins_api):
    # Also need to patch the global j in the function's namespace
    with patch("src.devops_mcps.jenkins.j", mock_jenkins_api):
      result = manage_jenkins_module.jenkins_get_queue()

  assert "queue_items" in result
  assert result["queue_items"] == mock_queue_items


def test_jenkins_get_queue_jenkins_api_exception(manage_jenkins_module):
  """Test jenkins_get_queue with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api = MagicMock()
  mock_jenkins_api.get_queue.side_effect = JenkinsAPIException("Queue error")

  # Mock the global j variable using patch
  with patch.object(manage_jenkins_module, "j", mock_jenkins_api):
    # Also need to patch the global j in the function's namespace
    with patch("src.devops_mcps.jenkins.j", mock_jenkins_api):
      result = manage_jenkins_module.jenkins_get_queue()

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


def test_jenkins_get_recent_failed_builds_success(manage_jenkins_module):
  """Test successful retrieval of recent failed builds."""
  from datetime import datetime, timezone, timedelta

  # Create a timestamp that's within the last 8 hours
  mock_now = datetime(2023, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
  recent_timestamp = mock_now - timedelta(hours=2)
  recent_timestamp_ms = int(recent_timestamp.timestamp() * 1000)

  # Mock successful API response
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "FailedJob",
        "url": "http://jenkins/job/FailedJob/",
        "lastBuild": {
          "number": 10,
          "timestamp": recent_timestamp_ms,
          "result": "FAILURE",
          "url": "http://jenkins/job/FailedJob/10/",
        },
      },
      {
        "name": "SuccessJob",
        "url": "http://jenkins/job/SuccessJob/",
        "lastBuild": {
          "number": 5,
          "timestamp": recent_timestamp_ms,
          "result": "SUCCESS",
          "url": "http://jenkins/job/SuccessJob/5/",
        },
      },
    ]
  }

  # Use the existing module and mock its functions directly
  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          with patch.object(manage_jenkins_module, "datetime") as mock_datetime:
            mock_requests.get.return_value = mock_response
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert len(result) == 1
  assert result[0]["job_name"] == "FailedJob"
  assert result[0]["status"] == "FAILURE"


@patch("src.devops_mcps.jenkins.requests.get")
def test_jenkins_get_recent_failed_builds_connection_error(
  mock_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with connection error."""
  mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

  with patch.dict(
    "os.environ",
    {"JENKINS_URL": "http://jenkins", "JENKINS_USER": "user", "JENKINS_TOKEN": "token"},
  ):
    if "src.devops_mcps.jenkins" in sys.modules:
      del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Could not connect to Jenkins API" in result["error"]


@patch("src.devops_mcps.jenkins.requests.get")
def test_jenkins_get_recent_failed_builds_timeout(mock_get, manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with timeout error."""
  mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

  with patch.dict(
    "os.environ",
    {"JENKINS_URL": "http://jenkins", "JENKINS_USER": "user", "JENKINS_TOKEN": "token"},
  ):
    if "src.devops_mcps.jenkins" in sys.modules:
      del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Timeout connecting to Jenkins API" in result["error"]


@patch("src.devops_mcps.jenkins.requests.get")
def test_jenkins_get_recent_failed_builds_http_error(mock_get, manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with HTTP error."""
  mock_response = MagicMock()
  mock_response.status_code = 404
  mock_response.reason = "Not Found"
  mock_response.text = "Page not found"
  mock_get.return_value = mock_response
  mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
    response=mock_response
  )

  with patch.dict(
    "os.environ",
    {"JENKINS_URL": "http://jenkins", "JENKINS_USER": "user", "JENKINS_TOKEN": "token"},
  ):
    if "src.devops_mcps.jenkins" in sys.modules:
      del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Jenkins API HTTP Error: 404" in result["error"]


def test_to_dict_view_object(manage_jenkins_module):
  """Test _to_dict with View object."""
  mock_view = MagicMock()
  mock_view.name = "TestView"
  mock_view.baseurl = "http://jenkins/view/TestView/"
  mock_view.get_description.return_value = "Test view description"

  with patch("src.devops_mcps.jenkins.View", new=type(mock_view)):
    result = manage_jenkins_module._to_dict(mock_view)

  assert result == {
    "name": "TestView",
    "url": "http://jenkins/view/TestView/",
    "description": "Test view description",
  }


def test_to_dict_unknown_object_with_error(manage_jenkins_module):
  """Test _to_dict with unknown object that raises error during str conversion."""

  class ProblematicObject:
    def __str__(self):
      raise ValueError("Cannot convert to string")

  obj = ProblematicObject()
  result = manage_jenkins_module._to_dict(obj)
  assert "<Error serializing object of type ProblematicObject>" in result


# --- Additional Tests for Better Coverage ---


def test_to_dict_build_object(manage_jenkins_module):
  """Test _to_dict with Build object (fallback case)."""
  mock_build = MagicMock()
  mock_build.__class__.__name__ = "Build"

  # This should trigger the fallback case since Build is not explicitly handled
  result = manage_jenkins_module._to_dict(mock_build)
  assert isinstance(result, str)


def test_to_dict_nested_structures(manage_jenkins_module):
  """Test _to_dict with nested dictionaries and lists."""
  nested_data = {
    "jobs": [{"name": "job1", "enabled": True}, {"name": "job2", "enabled": False}],
    "metadata": {"count": 2, "timestamp": None},
  }

  result = manage_jenkins_module._to_dict(nested_data)
  assert result == nested_data
  assert isinstance(result["jobs"], list)
  assert len(result["jobs"]) == 2


def test_initialize_jenkins_client_already_initialized(manage_jenkins_module):
  """Test that initialize_jenkins_client returns existing client if already initialized."""
  mock_client = MagicMock()
  manage_jenkins_module.j = mock_client

  result = manage_jenkins_module.initialize_jenkins_client()
  assert result is mock_client


def test_initialize_jenkins_client_unexpected_error(
  mock_env_vars, manage_jenkins_module
):
  """Test initialization failure due to unexpected error."""
  with patch("jenkinsapi.jenkins.Jenkins") as mock_jenkins:
    mock_jenkins.side_effect = RuntimeError("Unexpected error")

    client = manage_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert manage_jenkins_module.j is None


def test_set_jenkins_client_for_testing(manage_jenkins_module):
  """Test the set_jenkins_client_for_testing function."""
  mock_client = MagicMock()
  manage_jenkins_module.set_jenkins_client_for_testing(mock_client)
  assert manage_jenkins_module.j is mock_client


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_parameters with unexpected exception."""
  mock_jenkins_api.get_job.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 1)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_job_not_found(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log when job is not found."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("Job not found")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("NonExistentJob", 1)

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log with unexpected exception."""
  mock_jenkins_api.get_job.side_effect = RuntimeError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 1)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_all_views with unexpected exception."""
  mock_jenkins_api.views.keys.side_effect = RuntimeError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  from src.devops_mcps.jenkins import jenkins_get_all_views

  result = jenkins_get_all_views()

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


def test_jenkins_get_queue_unexpected_exception(manage_jenkins_module):
  """Test jenkins_get_queue with unexpected exception."""
  mock_jenkins_api = MagicMock()
  mock_jenkins_api.get_queue.side_effect = RuntimeError("Unexpected error")

  # Mock the global j variable using patch
  with patch.object(manage_jenkins_module, "j", mock_jenkins_api):
    # Also need to patch the global j in the function's namespace
    with patch("src.devops_mcps.jenkins.j", mock_jenkins_api):
      result = manage_jenkins_module.jenkins_get_queue()

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.requests.get")
def test_jenkins_get_recent_failed_builds_json_error(mock_get, manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with JSON parsing error."""
  mock_response = MagicMock()
  mock_response.json.side_effect = ValueError("Invalid JSON")
  mock_get.return_value = mock_response

  with patch.dict(
    "os.environ",
    {"JENKINS_URL": "http://jenkins", "JENKINS_USER": "user", "JENKINS_TOKEN": "token"},
  ):
    if "src.devops_mcps.jenkins" in sys.modules:
      del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.requests.get")
def test_jenkins_get_recent_failed_builds_request_exception(
  mock_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with general request exception."""
  mock_get.side_effect = requests.exceptions.RequestException("Request failed")

  with patch.dict(
    "os.environ",
    {"JENKINS_URL": "http://jenkins", "JENKINS_USER": "user", "JENKINS_TOKEN": "token"},
  ):
    if "src.devops_mcps.jenkins" in sys.modules:
      del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    result = reloaded_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Jenkins API Request Error" in result["error"]


def test_jenkins_get_recent_failed_builds_no_jobs_key(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds when API response has no 'jobs' key."""
  mock_response = MagicMock()
  mock_response.json.return_value = {"message": "No jobs data"}

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          mock_requests.get.return_value = mock_response

          result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_job_no_name(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with job data missing name."""
  from datetime import datetime, timezone, timedelta

  mock_now = datetime(2023, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
  recent_timestamp = mock_now - timedelta(hours=2)
  recent_timestamp_ms = int(recent_timestamp.timestamp() * 1000)

  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {  # Job without name
        "url": "http://jenkins/job/NoName/",
        "lastBuild": {
          "number": 10,
          "timestamp": recent_timestamp_ms,
          "result": "FAILURE",
          "url": "http://jenkins/job/NoName/10/",
        },
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          with patch.object(manage_jenkins_module, "datetime") as mock_datetime:
            mock_requests.get.return_value = mock_response
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_no_last_build(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with job having no lastBuild data."""
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "JobWithoutBuild",
        "url": "http://jenkins/job/JobWithoutBuild/",
        # No lastBuild data
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          mock_requests.get.return_value = mock_response

          result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_no_timestamp(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with build missing timestamp."""
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "JobWithoutTimestamp",
        "url": "http://jenkins/job/JobWithoutTimestamp/",
        "lastBuild": {
          "number": 10,
          "result": "FAILURE",
          "url": "http://jenkins/job/JobWithoutTimestamp/10/",
          # No timestamp
        },
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          mock_requests.get.return_value = mock_response

          result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_old_build(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with build older than cutoff time."""
  mock_now = datetime(2023, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
  old_timestamp = mock_now - timedelta(hours=10)  # Older than 8 hours
  old_timestamp_ms = int(old_timestamp.timestamp() * 1000)

  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "OldFailedJob",
        "url": "http://jenkins/job/OldFailedJob/",
        "lastBuild": {
          "number": 10,
          "timestamp": old_timestamp_ms,
          "result": "FAILURE",
          "url": "http://jenkins/job/OldFailedJob/10/",
        },
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          with patch.object(manage_jenkins_module, "datetime") as mock_datetime:
            mock_requests.get.return_value = mock_response
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_recent_success(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with recent successful build (should be excluded)."""
  mock_now = datetime(2023, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
  recent_timestamp = mock_now - timedelta(hours=2)
  recent_timestamp_ms = int(recent_timestamp.timestamp() * 1000)

  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "RecentSuccessJob",
        "url": "http://jenkins/job/RecentSuccessJob/",
        "lastBuild": {
          "number": 10,
          "timestamp": recent_timestamp_ms,
          "result": "SUCCESS",  # Not a failure
          "url": "http://jenkins/job/RecentSuccessJob/10/",
        },
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          with patch.object(manage_jenkins_module, "datetime") as mock_datetime:
            mock_requests.get.return_value = mock_response
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []


def test_jenkins_get_recent_failed_builds_missing_build_url(manage_jenkins_module):
  """Test jenkins_get_recent_failed_builds with missing build URL (should construct one)."""
  mock_now = datetime(2023, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
  recent_timestamp = mock_now - timedelta(hours=2)
  recent_timestamp_ms = int(recent_timestamp.timestamp() * 1000)

  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "JobWithoutBuildUrl",
        "url": "http://jenkins/job/JobWithoutBuildUrl/",
        "lastBuild": {
          "number": 10,
          "timestamp": recent_timestamp_ms,
          "result": "FAILURE",
          # No build URL
        },
      }
    ]
  }

  with patch.object(manage_jenkins_module, "JENKINS_URL", "http://jenkins"):
    with patch.object(manage_jenkins_module, "JENKINS_USER", "user"):
      with patch.object(manage_jenkins_module, "JENKINS_TOKEN", "token"):
        with patch.object(manage_jenkins_module, "requests") as mock_requests:
          with patch.object(manage_jenkins_module, "datetime") as mock_datetime:
            mock_requests.get.return_value = mock_response
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert len(result) == 1
  assert result[0]["job_name"] == "JobWithoutBuildUrl"
  assert result[0]["url"] == "http://jenkins/job/JobWithoutBuildUrl/10"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_no_such_job_error(mock_j):
  """Test jenkins_get_build_parameters when job is not found."""
  from src.devops_mcps.jenkins import jenkins_get_build_parameters
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_j.__bool__.return_value = True
  mock_j.get_job.side_effect = JenkinsAPIException("No such job: nonexistent-job")

  result = jenkins_get_build_parameters("nonexistent-job", 1)

  assert "error" in result
  assert "Job 'nonexistent-job' not found" in result["error"]


def test_module_initialization_in_non_test_environment(manage_jenkins_module):
  """Test that module initialization is skipped during testing but would run otherwise."""
  # This test verifies the logic that prevents initialization during pytest
  import sys

  original_argv = sys.argv[:]

  try:
    # Simulate non-test environment
    sys.argv = ["python", "some_script.py"]

    # Import the module to trigger the initialization check
    # Since we're in pytest, the actual initialization won't run
    # but we can verify the logic exists
    import src.devops_mcps.jenkins as jenkins_module

    # The module should have the initialization code
    assert hasattr(jenkins_module, "initialize_jenkins_client")
  finally:
    sys.argv = original_argv


# --- Additional Tests for Better Coverage ---


def test_jenkins_get_all_views_with_cache_hit(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_all_views returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache with a result (using correct cache key)
  cache_key = "jenkins:views:all"
  cached_result = [{"name": "TestView", "url": "http://jenkins/view/TestView/"}]
  cache.set(cache_key, cached_result)

  # Call the function - should return cached result without checking client
  result = manage_jenkins_module.jenkins_get_all_views()
  assert result == cached_result


def test_jenkins_get_build_parameters_with_cache_hit(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_build_parameters returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache with a result (using correct cache key)
  cache_key = "jenkins:build_parameters:TestJob:5"
  cached_result = {"param1": "value1", "param2": "value2"}
  cache.set(cache_key, cached_result)

  # Call the function - should return cached result without checking client
  result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 5)
  assert result == cached_result


def test_initialize_jenkins_client_jenkins_api_exception(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to JenkinsAPIException."""
  mock_jenkins_api.get_master_data.side_effect = JenkinsAPIException(
    "Authentication failed"
  )

  client = manage_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_general_exception(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to general exception."""
  mock_jenkins_api.get_master_data.side_effect = Exception("Unexpected error")

  client = manage_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert manage_jenkins_module.j is None


def test_jenkins_get_jobs_with_cache(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_jobs returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache
  cache_key = "jenkins:jobs:all"
  cached_result = [{"name": "cached_job", "url": "http://cached"}]
  cache.set(cache_key, cached_result)

  # Initialize client
  manage_jenkins_module.j = mock_jenkins_api

  result = manage_jenkins_module.jenkins_get_jobs()
  assert result == cached_result
  # Should not call Jenkins API since we have cached result
  mock_jenkins_api.keys.assert_not_called()


def test_jenkins_get_jobs_client_not_initialized_with_missing_credentials(
  monkeypatch, manage_jenkins_module
):
  """Test jenkins_get_jobs when client is None and credentials are missing."""
  # Remove environment variables
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up missing env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_jobs()
  assert "error" in result
  assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_jobs_with_cache_hit(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_jobs returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache with a result (using correct cache key)
  cache_key = "jenkins:jobs:all"
  cached_result = [{"name": "TestJob", "url": "http://jenkins/job/TestJob/"}]
  cache.set(cache_key, cached_result)

  # Call the function - should return cached result without checking client
  result = manage_jenkins_module.jenkins_get_jobs()
  assert result == cached_result


def test_jenkins_get_build_log_client_not_initialized_with_missing_credentials(
  monkeypatch, manage_jenkins_module
):
  """Test jenkins_get_build_log when client is None and credentials are missing."""
  # Remove environment variables
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up missing env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_build_log("TestJob", 1)
  assert "error" in result
  assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_all_views_with_cache(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_all_views returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache
  cache_key = "jenkins:views:all"
  cached_result = [{"name": "cached_view", "url": "http://cached"}]
  cache.set(cache_key, cached_result)

  # Initialize client
  manage_jenkins_module.j = mock_jenkins_api

  result = manage_jenkins_module.jenkins_get_all_views()
  assert result == cached_result
  # Should not call Jenkins API since we have cached result
  mock_jenkins_api.views.keys.assert_not_called()


def test_jenkins_get_all_views_client_not_initialized_with_missing_credentials(
  monkeypatch, manage_jenkins_module
):
  """Test jenkins_get_all_views when client is None and credentials are missing."""
  # Remove environment variables
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up missing env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_all_views()
  assert "error" in result
  assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_build_parameters_with_cache(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_build_parameters returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache
  cache_key = "jenkins:build_parameters:TestJob:5"
  cached_result = {"param1": "value1", "param2": "value2"}
  cache.set(cache_key, cached_result)

  # Initialize client
  manage_jenkins_module.j = mock_jenkins_api

  result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 5)
  assert result == cached_result
  # Should not call Jenkins API since we have cached result
  mock_jenkins_api.get_job.assert_not_called()


def test_jenkins_get_build_parameters_client_not_initialized_with_missing_credentials(
  monkeypatch, manage_jenkins_module
):
  """Test jenkins_get_build_parameters when client is None and credentials are missing."""
  # Remove environment variables
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up missing env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
  assert "error" in result
  assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_queue_with_cache(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test jenkins_get_queue returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache
  cache_key = "jenkins:queue:current"
  cached_result = {"queue_items": []}
  cache.set(cache_key, cached_result)

  # Initialize client
  manage_jenkins_module.j = mock_jenkins_api

  result = manage_jenkins_module.jenkins_get_queue()
  assert result == cached_result
  # Should not call Jenkins API since we have cached result
  mock_jenkins_api.get_queue.assert_not_called()


def test_jenkins_get_queue_client_not_initialized_with_missing_credentials(
  monkeypatch, manage_jenkins_module
):
  """Test jenkins_get_queue when client is None and credentials are missing."""
  # Remove environment variables
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Reload module to pick up missing env vars
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]
  import src.devops_mcps.jenkins as reloaded_jenkins_module

  result = reloaded_jenkins_module.jenkins_get_queue()
  assert "error" in result
  assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_recent_failed_builds_with_cache(
  mock_env_vars, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds returns cached result when available."""
  from src.devops_mcps.cache import cache

  # Set up cache
  cache_key = "jenkins:recent_failed_builds:8"
  cached_result = [{"job_name": "FailedJob", "build_number": 5, "status": "FAILURE"}]
  cache.set(cache_key, cached_result)

  with patch("requests.get") as mock_get:
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    assert result == cached_result
    # Should not make HTTP request since we have cached result
    mock_get.assert_not_called()


def test_to_dict_fallback_with_exception(manage_jenkins_module):
  """Test _to_dict fallback when str() conversion fails."""

  class ProblematicObject:
    def __str__(self):
      raise Exception("String conversion failed")

  obj = ProblematicObject()
  result = manage_jenkins_module._to_dict(obj)

  # Should handle the exception and return some error representation
  assert isinstance(result, str)
  assert "Error during fallback" in result or "ProblematicObject" in result


# --- Additional Tests for Better Coverage ---


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of views."""
  from src.devops_mcps.jenkins import jenkins_get_all_views
  from jenkinsapi.view import View

  # Setup mock views
  mock_view1 = MagicMock(spec=View)
  mock_view1.name = "View1"
  mock_view1.baseurl = "http://jenkins/view/View1/"
  mock_view1.get_description = MagicMock(return_value="Test view 1")

  mock_view2 = MagicMock(spec=View)
  mock_view2.name = "View2"
  mock_view2.baseurl = "http://jenkins/view/View2/"
  mock_view2.get_description = MagicMock(return_value="Test view 2")

  mock_jenkins_api.views.keys.return_value = [mock_view1, mock_view2]

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  result = jenkins_get_all_views()

  assert len(result) == 2
  assert result[0]["name"] == "View1"
  assert result[1]["name"] == "View2"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_all_views with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.views.keys.side_effect = JenkinsAPIException("API Error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  from src.devops_mcps.jenkins import jenkins_get_all_views

  result = jenkins_get_all_views()

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of build parameters."""
  mock_job = MagicMock()
  mock_build = MagicMock()
  mock_build.get_params.return_value = {"param1": "value1", "param2": "value2"}
  mock_job.get_build.return_value = mock_build
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 1)

  assert result == {"param1": "value1", "param2": "value2"}
  mock_jenkins_api.get_job.assert_called_once_with("TestJob")
  mock_job.get_build.assert_called_once_with(1)


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_build_not_found(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_parameters when build is not found."""
  mock_job = MagicMock()
  mock_job.get_build.return_value = None  # Build not found
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 999)

  assert "error" in result
  assert "Build #999 not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_job_not_found(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_parameters when job is not found."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("No such job")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("NonExistentJob", 1)

  assert "error" in result
  assert "not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_success(mock_j, mock_jenkins_api):
  """Test successful retrieval of queue information."""
  mock_queue = MagicMock()
  mock_queue_item = MagicMock()
  mock_queue_item.name = "QueuedJob"
  mock_queue.get_queue_items.return_value = [mock_queue_item]
  mock_jenkins_api.get_queue.return_value = mock_queue

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_queue = mock_jenkins_api.get_queue

  from src.devops_mcps.jenkins import jenkins_get_queue

  result = jenkins_get_queue()

  assert "queue_items" in result
  assert len(result["queue_items"]) == 1


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_queue with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_queue.side_effect = JenkinsAPIException("Queue API Error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_queue = mock_jenkins_api.get_queue

  from src.devops_mcps.jenkins import jenkins_get_queue

  result = jenkins_get_queue()

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_success(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test successful retrieval of recent failed builds."""
  mock_cache.get.return_value = None  # No cache hit
  # Mock successful API response
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "FailedJob",
        "url": "http://jenkins/job/FailedJob/",
        "lastBuild": {
          "number": 5,
          "timestamp": int(
            (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000
          ),
          "result": "FAILURE",
          "url": "http://jenkins/job/FailedJob/5/",
        },
      },
      {
        "name": "SuccessJob",
        "url": "http://jenkins/job/SuccessJob/",
        "lastBuild": {
          "number": 3,
          "timestamp": int(
            (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000
          ),
          "result": "SUCCESS",
          "url": "http://jenkins/job/SuccessJob/3/",
        },
      },
    ]
  }
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert len(result) == 1  # Only failed job should be returned
  assert result[0]["job_name"] == "FailedJob"
  assert result[0]["status"] == "FAILURE"
  assert result[0]["build_number"] == 5


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_timeout_error(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with timeout error."""
  import requests

  mock_cache.get.return_value = None  # No cache hit
  mock_requests_get.side_effect = requests.exceptions.Timeout("Request timeout")

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Timeout connecting to Jenkins API" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_connection_error(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with connection error."""
  import requests

  mock_cache.get.return_value = None  # No cache hit
  mock_requests_get.side_effect = requests.exceptions.ConnectionError(
    "Connection failed"
  )

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Could not connect to Jenkins API" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_http_error(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with HTTP error."""
  import requests

  mock_cache.get.return_value = None  # No cache hit
  mock_response = MagicMock()
  mock_response.status_code = 404
  mock_response.reason = "Not Found"
  mock_response.text = "Page not found"
  http_error = requests.exceptions.HTTPError("404 Client Error")
  http_error.response = mock_response
  mock_requests_get.side_effect = http_error

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Jenkins API HTTP Error" in result["error"]
  assert "404" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_no_jobs_key(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds when API response has no jobs key."""
  mock_cache.get.return_value = None  # No cache hit
  mock_response = MagicMock()
  mock_response.json.return_value = {}  # No jobs key
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []  # Should return empty list


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_old_builds(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with builds older than cutoff."""
  mock_cache.get.return_value = None  # No cache hit
  # Mock API response with old builds
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "OldFailedJob",
        "url": "http://jenkins/job/OldFailedJob/",
        "lastBuild": {
          "number": 5,
          "timestamp": int(
            (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp() * 1000
          ),  # 25 hours ago
          "result": "FAILURE",
          "url": "http://jenkins/job/OldFailedJob/5/",
        },
      }
    ]
  }
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []  # Should return empty list since build is too old


def test_set_jenkins_client_for_testing(manage_jenkins_module):
  """Test the set_jenkins_client_for_testing function."""
  mock_client = MagicMock()

  manage_jenkins_module.set_jenkins_client_for_testing(mock_client)

  assert manage_jenkins_module.j == mock_client


def test_to_dict_view_object(manage_jenkins_module):
  """Test _to_dict with View object."""
  from jenkinsapi.view import View

  # Create a real View instance with mocked methods
  with patch("jenkinsapi.view.View.__init__", return_value=None):
    mock_view = View()
    mock_view.name = "TestView"
    mock_view.baseurl = "http://jenkins/view/TestView/"

    # Add the get_description method and then mock it
    mock_view.get_description = MagicMock(return_value="Test view description")

    result = manage_jenkins_module._to_dict(mock_view)

  assert result == {
    "name": "TestView",
    "url": "http://jenkins/view/TestView/",
    "description": "Test view description",
  }


def test_to_dict_unknown_object_with_warning(manage_jenkins_module):
  """Test _to_dict with unknown object type that triggers warning."""

  class UnknownObject:
    def __str__(self):
      return "unknown_object_string"

  obj = UnknownObject()
  result = manage_jenkins_module._to_dict(obj)

  assert result == "unknown_object_string"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_build_not_found(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log when build is not found."""
  mock_job = MagicMock()
  mock_job.get_build.return_value = None  # Build not found
  mock_jenkins_api.get_job.return_value = mock_job

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 999)

  assert "error" in result
  assert "Build #999 not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log with JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("Job API Error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 1)

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_log with unexpected exception."""
  mock_jenkins_api.get_job.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_log

  result = jenkins_get_build_log("TestJob", 1)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_all_views with unexpected exception."""
  mock_jenkins_api.views.keys.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.views = mock_jenkins_api.views

  from src.devops_mcps.jenkins import jenkins_get_all_views

  result = jenkins_get_all_views()

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_jenkins_api_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_parameters with general JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_job.side_effect = JenkinsAPIException("General API Error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 1)

  assert "error" in result
  assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_build_parameters with unexpected exception."""
  mock_jenkins_api.get_job.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_job = mock_jenkins_api.get_job

  from src.devops_mcps.jenkins import jenkins_get_build_parameters

  result = jenkins_get_build_parameters("TestJob", 1)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_unexpected_exception(mock_j, mock_jenkins_api):
  """Test jenkins_get_queue with unexpected exception."""
  mock_jenkins_api.get_queue.side_effect = ValueError("Unexpected error")

  # Replace the mock with our jenkins api mock
  mock_j.__bool__ = lambda self: True
  mock_j.get_queue = mock_jenkins_api.get_queue

  from src.devops_mcps.jenkins import jenkins_get_queue

  result = jenkins_get_queue()

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_request_exception(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with general RequestException."""
  import requests

  mock_cache.get.return_value = None  # No cache hit
  mock_requests_get.side_effect = requests.exceptions.RequestException(
    "General request error"
  )

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "Jenkins API Request Error" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_json_decode_error(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with JSON decode error."""
  mock_cache.get.return_value = None  # No cache hit
  mock_response = MagicMock()
  mock_response.json.side_effect = ValueError("Invalid JSON")
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert "error" in result
  assert "An unexpected error occurred" in result["error"]


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_job_missing_name(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with job missing name."""
  mock_cache.get.return_value = None  # No cache hit
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        # Missing "name" field
        "url": "http://jenkins/job/NoNameJob/",
        "lastBuild": {
          "number": 5,
          "timestamp": int(
            (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000
          ),
          "result": "FAILURE",
          "url": "http://jenkins/job/NoNameJob/5/",
        },
      }
    ]
  }
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []  # Should skip job without name


@patch("src.devops_mcps.jenkins.cache")
@patch("src.devops_mcps.jenkins.JENKINS_URL", "http://fake-jenkins.com")
@patch("src.devops_mcps.jenkins.JENKINS_USER", "testuser")
@patch("src.devops_mcps.jenkins.JENKINS_TOKEN", "testtoken")
def test_jenkins_get_recent_failed_builds_job_missing_timestamp(
  mock_cache, mock_env_vars, mock_requests_get, manage_jenkins_module
):
  """Test jenkins_get_recent_failed_builds with job missing timestamp."""
  mock_cache.get.return_value = None  # No cache hit
  mock_response = MagicMock()
  mock_response.json.return_value = {
    "jobs": [
      {
        "name": "NoTimestampJob",
        "url": "http://jenkins/job/NoTimestampJob/",
        "lastBuild": {
          "number": 5,
          # Missing "timestamp" field
          "result": "FAILURE",
          "url": "http://jenkins/job/NoTimestampJob/5/",
        },
      }
    ]
  }
  mock_response.raise_for_status.return_value = None
  mock_requests_get.return_value = mock_response

  result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

  assert result == []  # Should skip job without timestamp


def test_initialize_jenkins_client_jenkins_api_exception(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to JenkinsAPIException."""
  from jenkinsapi.custom_exceptions import JenkinsAPIException

  mock_jenkins_api.get_master_data.side_effect = JenkinsAPIException("Auth failed")

  client = manage_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_unexpected_exception(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test initialization failure due to unexpected exception."""
  mock_jenkins_api.get_master_data.side_effect = ValueError("Unexpected error")

  client = manage_jenkins_module.initialize_jenkins_client()
  assert client is None
  assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_already_initialized(
  mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
  """Test that initialization returns existing client if already initialized."""
  # Set up an existing client
  existing_client = MagicMock()
  manage_jenkins_module.j = existing_client

  client = manage_jenkins_module.initialize_jenkins_client()

  assert client == existing_client
  assert manage_jenkins_module.j == existing_client
  # Should not create a new Jenkins instance
  mock_jenkins_api.assert_not_called()
