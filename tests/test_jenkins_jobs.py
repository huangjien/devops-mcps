"""Tests for Jenkins job operations."""

import pytest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job


def test_get_jobs_no_client(manage_jenkins_module):
    """Test getting jobs when client is not initialized."""
    manage_jenkins_module.j = None  # Ensure client is None
    result = manage_jenkins_module.jenkins_get_jobs()
    assert result == {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }


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

    mock_jenkins_api.values.return_value = [mock_job1, mock_job2]

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values

    result = jenkins_get_jobs()

    assert len(result) == 2
    assert result[0]["name"] == "Job1"
    assert result[1]["name"] == "Job2"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_jenkins_api_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs with JenkinsAPIException."""
    from jenkinsapi.custom_exceptions import JenkinsAPIException

    mock_jenkins_api.values.side_effect = JenkinsAPIException("API Error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values

    from src.devops_mcps.jenkins import jenkins_get_jobs

    result = jenkins_get_jobs()

    assert "error" in result
    assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_unexpected_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs with unexpected exception."""
    mock_jenkins_api.values.side_effect = ValueError("Unexpected error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values

    from src.devops_mcps.jenkins import jenkins_get_jobs

    result = jenkins_get_jobs()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


def test_jenkins_get_jobs_with_cache(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_jobs with caching."""
    from src.devops_mcps.cache import cache

    # Setup mock job
    mock_job = MagicMock()
    mock_job.name = "TestJob"
    mock_job.baseurl = "http://jenkins/job/TestJob/"
    mock_job.is_enabled.return_value = True
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.return_value = 1
    mock_job.get_last_buildurl.return_value = "http://jenkins/job/TestJob/1/"

    mock_jenkins_api.values.return_value = [mock_job]
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    # First call should cache the result
    result1 = manage_jenkins_module.jenkins_get_jobs()
    assert len(result1) == 1
    assert result1[0]["name"] == "TestJob"

    # Verify result is cached
    cached_result = cache.get("jenkins:jobs:all")
    assert cached_result is not None


def test_jenkins_get_jobs_client_not_initialized_with_missing_credentials(
    monkeypatch, manage_jenkins_module
):
    """Test jenkins_get_jobs when client is not initialized due to missing credentials."""
    # Remove environment variables
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)

    # Ensure client is None
    manage_jenkins_module.j = None

    result = manage_jenkins_module.jenkins_get_jobs()
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_jobs_with_cache_hit(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_jobs with cache hit."""
    from src.devops_mcps.cache import cache

    # Initialize Jenkins client
    manage_jenkins_module.j = mock_jenkins_api

    # Pre-populate cache
    cached_jobs = [{"name": "CachedJob", "url": "http://jenkins/job/CachedJob/"}]
    cache.set("jenkins:jobs:all", cached_jobs, ttl=300)

    # Call should return cached result without hitting Jenkins API
    result = manage_jenkins_module.jenkins_get_jobs()
    assert result == cached_jobs


def test_jenkins_get_jobs_with_values_method(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_jobs using j.values() method."""
    # Initialize Jenkins client
    manage_jenkins_module.j = mock_jenkins_api
    
    # Setup mock jobs
    from jenkinsapi.job import Job
    mock_job1 = MagicMock(spec=Job)
    mock_job1.name = "Job1"
    mock_job1.baseurl = "http://jenkins/job/Job1/"
    mock_job1.is_enabled.return_value = True
    mock_job1.is_queued.return_value = False
    mock_job1.get_last_buildnumber.return_value = 10
    mock_job1.get_last_build_url = MagicMock()
    mock_job1.get_last_build_url.return_value = "http://jenkins/job/Job1/10/"
    mock_job1.get_last_buildurl = MagicMock()
    mock_job1.get_last_buildurl.return_value = "http://jenkins/job/Job1/10/"

    mock_job2 = MagicMock(spec=Job)
    mock_job2.name = "Job2"
    mock_job2.baseurl = "http://jenkins/job/Job2/"
    mock_job2.is_enabled.return_value = False
    mock_job2.is_queued.return_value = True
    mock_job2.get_last_buildnumber.return_value = 5
    mock_job2.get_last_build_url = MagicMock()
    mock_job2.get_last_build_url.return_value = "http://jenkins/job/Job2/5/"
    mock_job2.get_last_buildurl = MagicMock()
    mock_job2.get_last_buildurl.return_value = "http://jenkins/job/Job2/5/"

    # Mock the values() method to return job objects
    mock_jenkins_api.values.return_value = [mock_job1, mock_job2]
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_jobs()

    assert len(result) == 2
    assert result[0]["name"] == "Job1"
    assert result[0]["url"] == "http://jenkins/job/Job1/"
    assert result[0]["is_enabled"] is True
    assert result[0]["is_queued"] is False
    assert result[0]["last_build_number"] == 10
    assert result[0]["last_build_url"] == "http://jenkins/job/Job1/10/"

    assert result[1]["name"] == "Job2"
    assert result[1]["url"] == "http://jenkins/job/Job2/"
    assert result[1]["is_enabled"] is False
    assert result[1]["is_queued"] is True
    assert result[1]["last_build_number"] == 5
    assert result[1]["last_build_url"] == "http://jenkins/job/Job2/5/"