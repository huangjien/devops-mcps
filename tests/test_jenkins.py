import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import requests

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Test Fixtures ---


@pytest.fixture(autouse=True)
def manage_jenkins_module():  # Remove mock_jenkins_api dependency
  """Fixture to manage the jenkins module import and cleanup."""
  # Ensure the module is fresh for each test if needed, especially for initialization logic
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]

  # Import after potential patches (or lack thereof in this simpler version)
  import src.devops_mcps.jenkins as jenkins_module

  # Reset the global client to None at the start of each test
  jenkins_module.j = None

  yield jenkins_module

  # Cleanup: reset the global client 'j'
  jenkins_module.j = None
  # Ensure module is removed again to avoid state leakage between tests
  if "src.devops_mcps.jenkins" in sys.modules:
    del sys.modules["src.devops_mcps.jenkins"]


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
  assert result == {"error": "Jenkins client not initialized."}


def test_get_build_log_no_client(manage_jenkins_module):
  """Test getting build log when client is not initialized."""
  manage_jenkins_module.j = None
  result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)
  assert result == {"error": "Jenkins client not initialized."}


def test_get_build_parameters_no_client(manage_jenkins_module):
  """Test getting parameters when client is not initialized."""
  manage_jenkins_module.j = None
  result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
  assert result == {"error": "Jenkins client not initialized."}


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

  assert result == {"error": "Jenkins credentials not configured."}
  mock_requests_get.assert_not_called()


def test_jenkins_get_all_views_no_client(manage_jenkins_module):
  """Test jenkins_get_all_views when client is not initialized."""
  manage_jenkins_module.j = None  # Ensure client is None
  result = manage_jenkins_module.jenkins_get_all_views()
  assert result == {"error": "Jenkins client not initialized."}
