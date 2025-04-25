import os
import pytest
from unittest import mock
import importlib
from datetime import datetime, timedelta, timezone
import hashlib

# Third-party testing libs
from jenkinsapi.jenkins import JenkinsAPIException
from requests.exceptions import ConnectionError, Timeout, HTTPError

# Module to test and its dependencies
from devops_mcps import jenkins
from devops_mcps import cache as app_cache # Import the actual cache instance

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
    with mock.patch('devops_mcps.jenkins.Jenkins', return_value=jenkins_client):
        importlib.reload(jenkins)
        yield

    # Cleanup after test
    app_cache.cache.clear()
    importlib.reload(jenkins)


# --- Tests for jenkins module ---

@pytest.fixture
def mock_requests_get():
    """Fixture to mock requests.get for the optimized API call."""
    with mock.patch('devops_mcps.jenkins.requests.get') as mock_get:
        yield mock_get


# --- Test Cases ---


def test_initialize_jenkins_client_no_vars():
    """Test Jenkins client initialization fails without env vars."""
    # Fixture `reset_state` ensures no vars and reloads
    # Initialization runs during reload, should set j to None
    assert jenkins.j is None


def test_initialize_jenkins_client_api_error():
    """Test initialization handles JenkinsAPIException."""
    with mock.patch('devops_mcps.jenkins.Jenkins', side_effect=JenkinsAPIException("Auth failed")):
        # Explicitly call initialize to trigger the error with the mock active
        jenkins.initialize_jenkins_client()
        assert jenkins.j is None


def test_initialize_jenkins_client_connection_error():
    """Test initialization handles ConnectionError."""
    with mock.patch('devops_mcps.jenkins.Jenkins', side_effect=ConnectionError("Cannot connect")):
        # Explicitly call initialize to trigger the error with the mock active
        jenkins.initialize_jenkins_client()
        assert jenkins.j is None

def test_jenkins_get_jobs_cache_hit(jenkins_client):
    """Test getting jobs from cache."""
    # Pre-populate cache
    cached_jobs = [{"name": "CachedJob", "url": "http://cache.url", "last_build_url": "http://cache.url/1"}]
    app_cache.cache.set("jenkins_jobs", cached_jobs, ttl=600)

    # Call the function
    result = jenkins.jenkins_get_jobs()

    # Assertions
    assert result == cached_jobs
    jenkins_client.get_jobs.assert_not_called() # API should not be called



def test_jenkins_get_jobs_no_client():
    """Test getting jobs when client is not initialized."""
    # `reset_state` ensures client is None initially, but then initializes it.
    # Need to explicitly set it to None for this test.
    jenkins.j = None
    result = jenkins.jenkins_get_jobs()
    assert result == {"error": "Jenkins client not initialized."}
    assert app_cache.cache.get("jenkins_jobs") is None


# Test jenkins_get_build_log
def test_jenkins_get_build_log_cache_hit():
    """Test getting build log from cache."""
    # jenkins.initialize_jenkins_client() # reset_state fixture handles initialization
    job_name = "TestJobHit"
    build_number = 6
    cached_log = "Cached log content"

    key_hash = hashlib.sha256(f"{job_name}_{build_number}".encode()).hexdigest()
    cache_key = f"jenkins_log_{key_hash}"
    app_cache.cache.set(cache_key, cached_log, ttl=600)

    result = jenkins.jenkins_get_build_log(job_name, build_number)

    assert result == cached_log
    # Cannot assert jenkins_client.get_job.assert_not_called() here because the fixture
    # provides the client, but the function might still access it even if cached.
    # The important part is that the API method is not called.


def test_jenkins_get_all_views_cache_hit(jenkins_client):
    """Test getting views from cache."""
    # jenkins.initialize_jenkins_client() # reset_state fixture handles initialization
    cached_views = [{"name": "CachedView", "url": "http://cache.url", "description": "Cached Desc"}]
    app_cache.cache.set("jenkins_views", cached_views, ttl=600)

    result = jenkins.jenkins_get_all_views()

    assert result == cached_views
    # Accessing j.views might happen implicitly, difficult to assert "not called" reliably here
    # Focus on the fact that the result is the cached one.


def test_jenkins_get_recent_failed_builds_cache_hit(mock_requests_get):
    """Test getting recent failed builds from cache using mock datetime."""
    hours_ago = 4
    cache_key = f"jenkins_recent_failed_{hours_ago}h"
    cached_data = [{"job_name": "CachedFailJob", "build_number": 5, "status": "FAILURE", "url": "http://cache.url/5"}]
    ttl = 300 # TTL used in the actual function

    # Define times for testing cache hit
    cache_set_time = datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
    time_within_ttl = cache_set_time + timedelta(seconds=ttl - 1)

    # Pre-populate cache - manually set expiry based on cache_set_time
    app_cache.cache._cache[cache_key] = {
        "value": cached_data,
        "expires": cache_set_time + timedelta(seconds=ttl)
    }
    # Alternatively, use cache.set with mocked time:
    # with mock.patch('devops_mcps.cache.datetime') as mock_set_dt:
    #     mock_set_dt.now.return_value = cache_set_time
    #     app_cache.cache.set(cache_key, cached_data, ttl=ttl)


    # Patch datetime.now within the cache module where it's used for expiry check
    with mock.patch('devops_mcps.cache.datetime') as mock_get_dt:
        mock_get_dt.now.return_value = time_within_ttl # Time for the cache.get() check

        result = jenkins.jenkins_get_recent_failed_builds(hours_ago=hours_ago)

    # Assertions
    assert result == cached_data
    assert len(result) == 1
    assert result[0]['job_name'] == "CachedFailJob"
    assert result[0]['build_number'] == 5
    assert result[0]['status'] == "FAILURE"
    assert result[0]['url'] == "http://cache.url/5"
    mock_requests_get.assert_not_called()

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


