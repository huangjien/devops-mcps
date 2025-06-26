"""Tests for Jenkins build operations including logs and parameters."""

import pytest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build


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
    mock_build.get_console.return_value = "Latest build log content"
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_log

    result = jenkins_get_build_log("TestJob", 0)  # Should get latest build

    assert isinstance(result, str)
    assert "Latest build log content" in result
    mock_job.get_last_buildnumber.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_build_not_found(mock_j, mock_jenkins_api):
    """Test build log retrieval when build is not found."""
    mock_job = MagicMock()
    mock_job.get_build.side_effect = KeyError("Build not found")
    mock_jenkins_api.get_job.return_value = mock_job

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_log

    result = jenkins_get_build_log("TestJob", 999)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Build #999 not found for job TestJob" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_jenkins_api_exception(mock_j, mock_jenkins_api):
    """Test build log retrieval with JenkinsAPIException."""
    mock_jenkins_api.get_job.side_effect = JenkinsAPIException("Jenkins API Error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_log

    result = jenkins_get_build_log("TestJob", 1)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_success(mock_j, mock_jenkins_api):
    """Test successful retrieval of build parameters."""
    mock_job = MagicMock()
    mock_build = MagicMock()
    mock_build.get_params.return_value = {
        "parameters": [{"name": "PARAM1", "value": "value1"}]
    }
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_parameters

    result = jenkins_get_build_parameters("TestJob", 1)

    assert isinstance(result, dict)
    assert "parameters" in result
    assert result["parameters"][0]["name"] == "PARAM1"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_build_not_found(mock_j, mock_jenkins_api):
    """Test build parameters retrieval when build is not found."""
    mock_job = MagicMock()
    mock_job.get_build.side_effect = KeyError("Build not found")
    mock_jenkins_api.get_job.return_value = mock_job

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_parameters

    result = jenkins_get_build_parameters("TestJob", 999)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Build not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_job_not_found(mock_j, mock_jenkins_api):
    """Test build parameters retrieval when job is not found."""
    mock_jenkins_api.get_job.side_effect = KeyError("Job not found")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_parameters

    result = jenkins_get_build_parameters("NonExistentJob", 1)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Job not found" in result["error"]


def test_jenkins_get_build_log_client_not_initialized_with_missing_credentials(
    monkeypatch, manage_jenkins_module
):
    """Test jenkins_get_build_log when client is not initialized due to missing credentials."""
    # Remove environment variables
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)

    # Ensure client is None
    manage_jenkins_module.j = None

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_build_parameters_with_cache(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_parameters with caching."""
    from src.devops_mcps.cache import cache

    # Setup mock build with parameters
    mock_job = MagicMock()
    mock_build = MagicMock()
    mock_build.get_params.return_value = {
        "parameters": [{"name": "TEST_PARAM", "value": "test_value"}]
    }
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    # First call should cache the result
    result1 = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
    assert "parameters" in result1
    assert result1["parameters"][0]["name"] == "TEST_PARAM"

    # Verify result is cached
    cache_key = "jenkins:build_parameters:TestJob:1"
    cached_result = cache.get(cache_key)
    assert cached_result is not None


def test_jenkins_get_build_parameters_client_not_initialized_with_missing_credentials(
    monkeypatch, manage_jenkins_module
):
    """Test jenkins_get_build_parameters when client is not initialized due to missing credentials."""
    # Remove environment variables
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)

    # Ensure client is None
    manage_jenkins_module.j = None

    result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_build_parameters_with_cache_hit(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_parameters with cache hit."""
    from src.devops_mcps.cache import cache

    # Pre-populate cache
    cached_params = {"parameters": [{"name": "CACHED_PARAM", "value": "cached_value"}]}
    cache_key = "jenkins:build_parameters:TestJob:1"
    cache.set(cache_key, cached_params, ttl=300)

    # Call should return cached result without hitting Jenkins API
    result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)
    assert result == cached_params


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
    """Test build log retrieval when job is not found."""
    mock_jenkins_api.get_job.side_effect = KeyError("Job not found")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_log

    result = jenkins_get_build_log("NonExistentJob", 1)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Job not found" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_unexpected_exception(mock_j, mock_jenkins_api):
    """Test build log retrieval with unexpected exception."""
    mock_jenkins_api.get_job.side_effect = ValueError("Unexpected error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job

    from src.devops_mcps.jenkins import jenkins_get_build_log

    result = jenkins_get_build_log("TestJob", 1)

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


def test_jenkins_get_build_log_log_sanitization(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test that build logs are properly sanitized of special characters."""
    # Setup mock job and build with log containing special characters
    mock_job = MagicMock()
    mock_build = MagicMock()
    # Include various special characters that should be sanitized
    mock_build.get_console.return_value = (
        "Build log with special chars: \x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f"
    )
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)

    # Verify that special characters are removed
    assert isinstance(result, str)
    assert "Build log with special chars:" in result
    # Verify that control characters are removed
    for char_code in range(32):  # Control characters 0-31
        if char_code not in [9, 10, 13]:  # Except tab, newline, carriage return
            assert chr(char_code) not in result
    assert "\x7f" not in result  # DEL character


def test_jenkins_get_build_log_utf8_encoding(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test that build logs handle UTF-8 characters properly."""
    # Setup mock job and build with UTF-8 content
    mock_job = MagicMock()
    mock_build = MagicMock()
    mock_build.get_console.return_value = "Build log with UTF-8: 你好世界 🚀 café"
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)

    # Verify that UTF-8 characters are preserved
    assert isinstance(result, str)
    assert "你好世界" in result
    assert "🚀" in result
    assert "café" in result


def test_jenkins_get_build_log_length_truncation(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test that build logs are truncated based on LOG_LENGTH."""
    import os
    
    # Set a small LOG_LENGTH for testing
    os.environ['LOG_LENGTH'] = '50'
    
    # Setup mock job and build with long log content
    mock_job = MagicMock()
    mock_build = MagicMock()
    long_log = "This is a very long build log that should be truncated " * 10
    mock_build.get_console.return_value = long_log
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)

    # Verify that log is truncated to LOG_LENGTH
    assert isinstance(result, str)
    assert len(result) <= 50
    
    # Clean up
    if 'LOG_LENGTH' in os.environ:
        del os.environ['LOG_LENGTH']


def test_jenkins_get_build_log_non_string_log(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test handling of non-string log content."""
    # Setup mock job and build with non-string log content
    mock_job = MagicMock()
    mock_build = MagicMock()
    mock_build.get_console.return_value = None  # Non-string content
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)

    # Should handle non-string content gracefully
    assert isinstance(result, str)
    assert result == "None"  # Should convert to string


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_no_such_job_error(mock_j):
    """Test jenkins_get_build_parameters with UnknownJob error."""
    from jenkinsapi.custom_exceptions import UnknownJob
    from src.devops_mcps.jenkins import jenkins_get_build_parameters

    mock_j.__bool__ = lambda self: True
    mock_j.get_job.side_effect = UnknownJob("Job not found")

    result = jenkins_get_build_parameters("NonExistentJob", 1)

    assert "error" in result
    assert "Job not found" in result["error"]


def test_jenkins_get_build_parameters_no_such_job_specific_error(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_parameters with specific UnknownJob handling."""
    from jenkinsapi.custom_exceptions import UnknownJob
    
    mock_jenkins_api.get_job.side_effect = UnknownJob("Job 'TestJob' not found")
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)

    assert "error" in result
    assert "Job 'TestJob' not found" in result["error"]


def test_jenkins_get_build_parameters_other_jenkins_error(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_parameters with other JenkinsAPIException."""
    mock_jenkins_api.get_job.side_effect = JenkinsAPIException("Other Jenkins error")
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_parameters("TestJob", 1)

    assert "error" in result
    assert "Jenkins API Error" in result["error"]
    assert "Other Jenkins error" in result["error"]


def test_jenkins_get_build_log_build_none(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_log when build is None."""
    mock_job = MagicMock()
    mock_job.get_build.return_value = None
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", 1)

    assert "error" in result
    assert "Build #1 not found for job TestJob" in result["error"]


def test_jenkins_get_build_log_negative_build_number(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_build_log with negative build number (should get latest)."""
    mock_job = MagicMock()
    mock_job.get_last_buildnumber.return_value = 42
    mock_build = MagicMock()
    mock_build.get_console.return_value = "Latest build log content"
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_build_log("TestJob", -1)

    assert isinstance(result, str)
    assert "Latest build log content" in result
    # Verify that get_last_buildnumber was called to get the latest build
    mock_job.get_last_buildnumber.assert_called_once()
    # Verify that get_build was called with the latest build number
    mock_job.get_build.assert_called_once_with(42)