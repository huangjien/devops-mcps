import pytest
from unittest import mock
import importlib

# Third-party testing libs
from jenkinsapi.jenkins import JenkinsAPIException
from requests.exceptions import ConnectionError, Timeout, HTTPError

# Module to test and its dependencies
from devops_mcps import jenkins
from devops_mcps import cache as app_cache  # Import the actual cache instance


# --- Fixtures ---
@pytest.fixture
def jenkins_client():
  """Fixture to mock the Jenkins client with proper spec"""
  from jenkinsapi.jenkins import Jenkins

  mock_client = mock.MagicMock(spec=Jenkins)
  mock_client.get_master_data.return_value = {"nodeName": "test-master"}
  mock_client.get_jobs.return_value = iter([])
  mock_client.get_job.return_value = mock.MagicMock()
  mock_client.views.items.return_value = []
  return mock_client


@pytest.fixture(autouse=True)
def reset_state(monkeypatch, jenkins_client):
  """Fixture to reset module state between tests"""
  # Mock environment variables
  monkeypatch.setenv("JENKINS_URL", "http://localhost:8080")
  monkeypatch.setenv("JENKINS_USER", "testuser")
  monkeypatch.setenv("JENKINS_TOKEN", "testtoken")
  monkeypatch.setenv("LOG_LENGTH", "500")

  # Clear cache before each test
  app_cache.cache.clear()

  # Patch Jenkins client and reload module
  with mock.patch("devops_mcps.jenkins.Jenkins", return_value=jenkins_client):
    importlib.reload(jenkins)
    yield

  # Cleanup after test
  app_cache.cache.clear()
  importlib.reload(jenkins)


# --- Tests for jenkins module ---


@pytest.fixture
def mock_requests_get():
  """Fixture to mock requests.get for the optimized API call."""
  with mock.patch("devops_mcps.jenkins.requests.get") as mock_get:
    yield mock_get


# --- Test Cases ---


def test_initialize_jenkins_client_no_vars():
  """Test Jenkins client initialization fails without env vars."""
  # Fixture `reset_state` ensures no vars and reloads
  # Initialization runs during reload, should set j to None
  assert jenkins.j is None


def test_initialize_jenkins_client_api_error():
  """Test initialization handles JenkinsAPIException."""
  with mock.patch(
    "devops_mcps.jenkins.Jenkins", side_effect=JenkinsAPIException("Auth failed")
  ):
    # Explicitly call initialize to trigger the error with the mock active
    jenkins.initialize_jenkins_client()
    assert jenkins.j is None


def test_initialize_jenkins_client_connection_error():
  """Test initialization handles ConnectionError."""
  with mock.patch(
    "devops_mcps.jenkins.Jenkins", side_effect=ConnectionError("Cannot connect")
  ):
    # Explicitly call initialize to trigger the error with the mock active
    jenkins.initialize_jenkins_client()
    assert jenkins.j is None


def test_jenkins_get_jobs_no_client():
  """Test getting jobs when client is not initialized."""
  # `reset_state` ensures client is None initially, but then initializes it.
  # Need to explicitly set it to None for this test.
  jenkins.j = None
  result = jenkins.jenkins_get_jobs()
  assert result == {"error": "Jenkins client not initialized."}
  assert app_cache.cache.get("jenkins_jobs") is None


# Test jenkins_get_build_log


def test_jenkins_get_recent_failed_builds_requests_error(mock_requests_get):
  """Test getting recent failed builds handles requests Timeout."""
  mock_requests_get.side_effect = Timeout("Request timed out")

  result = jenkins.jenkins_get_recent_failed_builds(hours_ago=1)

  assert "error" in result
  assert "Timeout connecting to Jenkins API" in result["error"]
  assert app_cache.cache.get("jenkins_recent_failed_1h") is None


def test_jenkins_get_recent_failed_builds_http_error(mock_requests_get):
  """Test getting recent failed builds handles HTTPError."""
  mock_response = mock.MagicMock()
  mock_response.status_code = 403
  mock_response.reason = "Forbidden"
  mock_response.text = "Auth error details"
  mock_requests_get.side_effect = HTTPError(response=mock_response)

  result = jenkins.jenkins_get_recent_failed_builds(hours_ago=1)

  assert result == {"error": "Jenkins API HTTP Error: 403 - Forbidden"}
  assert app_cache.cache.get("jenkins_recent_failed_1h") is None


def test_jenkins_get_recent_failed_builds_no_creds(monkeypatch):
  """Test getting recent failed builds without credentials."""
  # Clear any existing credentials
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  # Need to reload jenkins module to pick up the cleared env vars
  importlib.reload(jenkins)

  result = jenkins.jenkins_get_recent_failed_builds(hours_ago=1)
  assert result == {"error": "Jenkins credentials not configured."}
  assert app_cache.cache.get("jenkins_recent_failed_1h") is None
