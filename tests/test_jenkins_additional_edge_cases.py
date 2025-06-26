#!/usr/bin/env python3

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build
from jenkinsapi.view import View
import requests
from datetime import datetime, timezone, timedelta

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_with_empty_jobs_dict(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs when Jenkins returns empty jobs dictionary."""
    from src.devops_mcps.jenkins import jenkins_get_jobs
    
    # Mock empty jobs list
    mock_jenkins_api.values.return_value = []
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    result = jenkins_get_jobs()
    
    assert result == []
    mock_jenkins_api.values.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_with_none_jobs(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs when Jenkins returns None for jobs."""
    from src.devops_mcps.jenkins import jenkins_get_jobs
    
    # Mock None jobs by raising an exception
    mock_jenkins_api.values.side_effect = AttributeError("No jobs available")
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    result = jenkins_get_jobs()
    
    assert "error" in result
    mock_jenkins_api.values.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_with_job_having_no_attributes(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs with a job that has minimal attributes."""
    from src.devops_mcps.jenkins import jenkins_get_jobs
    
    # Create a mock job with minimal attributes
    mock_job = MagicMock(spec=Job)
    mock_job.name = "minimal-job"
    mock_job.baseurl = None  # Test None baseurl
    mock_job.is_enabled.side_effect = Exception("Method not available")
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.side_effect = Exception("No builds")
    mock_job.get_last_build_url = MagicMock()
    mock_job.get_last_build_url.side_effect = Exception("No builds")
    mock_job.get_last_buildurl = MagicMock()
    mock_job.get_last_buildurl.side_effect = Exception("No builds")
    
    mock_jenkins_api.values.return_value = [mock_job]
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    result = jenkins_get_jobs()
    
    # Should handle exceptions gracefully - either return list or error dict
    assert isinstance(result, (list, dict))
    if isinstance(result, list):
        assert len(result) == 1
        assert result[0]["name"] == "minimal-job"
    else:
        assert "error" in result  # Or return an error for problematic jobs
    mock_jenkins_api.values.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_with_very_long_log(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_log with a very long log that needs truncation."""
    from src.devops_mcps.jenkins import jenkins_get_build_log
    
    # Create a very long log (more than 5KB)
    very_long_log = "This is a test log line.\n" * 1000  # About 25KB
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_console.return_value = very_long_log
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    result = jenkins_get_build_log("test-job", 1)
    
    # jenkins_get_build_log returns the log content directly as a string
    assert isinstance(result, str)
    # Should be truncated to approximately 10KB (LOG_LENGTH default)
    assert len(result) <= 10240 + 100  # LOG_LENGTH + small buffer
    assert "This is a test log line." in result
    mock_jenkins_api.get_job.assert_called_once_with("test-job")
    mock_job.get_build.assert_called_once_with(1)


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_with_special_characters(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_log with special characters and encoding issues."""
    from src.devops_mcps.jenkins import jenkins_get_build_log
    
    # Log with special characters, ANSI codes, and potential encoding issues
    special_log = (
        "\x1b[31mERROR:\x1b[0m Build failed\n"
        "\x1b[32mSUCCESS:\x1b[0m Some step passed\n"
        "Unicode: ñáéíóú 中文 🚀\n"
        "Control chars: \x00\x01\x02\n"
        "Tabs and newlines:\t\r\n"
    )
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_console.return_value = special_log
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    result = jenkins_get_build_log("test-job", 1)
    
    # jenkins_get_build_log returns the log content directly as a string
    assert isinstance(result, str)
    # Should sanitize ANSI codes and control characters
    assert "\x1b[31m" not in result
    assert "\x1b[0m" not in result
    assert "\x00" not in result
    assert "ERROR:" in result
    assert "SUCCESS:" in result
    mock_jenkins_api.get_job.assert_called_once_with("test-job")


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_with_complex_parameters(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_parameters with complex parameter types."""
    from src.devops_mcps.jenkins import jenkins_get_build_parameters
    
    # Mock complex build parameters
    mock_parameters = {
        "string_param": "simple_value",
        "boolean_param": True,
        "choice_param": "option1",
        "multiline_param": "line1\nline2\nline3",
        "json_param": '{"key": "value", "nested": {"inner": "data"}}',
        "empty_param": "",
        "none_param": None,
        "numeric_param": 42,
        "float_param": 3.14,
        "list_param": ["item1", "item2", "item3"],
        "dict_param": {"nested_key": "nested_value"}
    }
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_params.return_value = mock_parameters
    mock_job.get_build.return_value = mock_build
    mock_j.get_job.return_value = mock_job
    
    result = jenkins_get_build_parameters("test-job", 1)
    
    # jenkins_get_build_parameters returns the parameters directly
    assert result["string_param"] == "simple_value"
    assert result["boolean_param"] is True
    assert result["numeric_param"] == 42
    assert result["float_param"] == 3.14
    assert result["none_param"] is None
    assert isinstance(result["list_param"], list)
    assert isinstance(result["dict_param"], dict)
    mock_j.get_job.assert_called_once_with("test-job")


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_with_nested_views(mock_j, mock_jenkins_api):
    """Test jenkins_get_all_views with nested and complex view structures."""
    from src.devops_mcps.jenkins import jenkins_get_all_views
    
    # Create mock views with different types
    mock_list_view = MagicMock(spec=View)
    mock_list_view.name = "ListView"
    mock_list_view.baseurl = "http://jenkins/view/ListView/"
    
    mock_my_view = MagicMock(spec=View)
    mock_my_view.name = "MyView"
    mock_my_view.baseurl = "http://jenkins/view/MyView/"
    
    mock_pipeline_view = MagicMock(spec=View)
    mock_pipeline_view.name = "PipelineView"
    mock_pipeline_view.baseurl = "http://jenkins/view/PipelineView/"
    
    # Mock views dictionary
    mock_views = {
        "ListView": mock_list_view,
        "MyView": mock_my_view,
        "PipelineView": mock_pipeline_view
    }
    
    mock_j.__bool__ = lambda self: True
    mock_j.views.values.return_value = [mock_list_view, mock_my_view, mock_pipeline_view]
    
    result = jenkins_get_all_views()
    
    assert len(result) == 3
    view_names = [view["name"] for view in result]
    assert "ListView" in view_names
    assert "MyView" in view_names
    assert "PipelineView" in view_names
    mock_j.views.values.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_malformed_timestamp(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with malformed timestamp data."""
    # Mock API response with malformed timestamp
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "job-with-bad-timestamp",
                "url": "http://jenkins/job/job-with-bad-timestamp/",
                "lastBuild": {
                    "number": 5,
                    "url": "http://jenkins/job/job-with-bad-timestamp/5/",
                    "result": "FAILURE",
                    "timestamp": "invalid-timestamp"  # Invalid timestamp
                }
            },
            {
                "name": "job-with-missing-timestamp",
                "url": "http://jenkins/job/job-with-missing-timestamp/",
                "lastBuild": {
                    "number": 6,
                    "url": "http://jenkins/job/job-with-missing-timestamp/6/",
                    "result": "FAILURE"
                    # Missing timestamp field
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    # Should handle malformed data gracefully - either return empty list or error dict
    assert isinstance(result, (list, dict))
    if isinstance(result, list):
        assert len(result) == 0  # Both jobs should be skipped due to timestamp issues
    else:
        assert "error" in result  # Or return an error for malformed data
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_connection_timeout(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with connection timeout."""
    mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out")
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    assert "error" in result
    assert "Timeout connecting to Jenkins API" in result["error"]
    assert "Connection timed out" in result["error"]
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_connection_error(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with connection error."""
    mock_requests_get.side_effect = requests.exceptions.ConnectionError("Could not connect")
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    assert "error" in result
    assert "Could not connect to Jenkins API" in result["error"]
    assert "Could not connect" in result["error"]
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_http_error_no_response(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with HTTP error that has no response object."""
    # Create an HTTPError without a response object
    http_error = requests.exceptions.HTTPError("HTTP Error occurred")
    http_error.response = None  # Explicitly set response to None
    mock_requests_get.side_effect = http_error
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    assert "error" in result
    assert "Jenkins API HTTP Error" in result["error"]
    assert "HTTP Error occurred" in result["error"]
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_zero_hours(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with zero hours (edge case)."""
    # Mock API response with a very recent failed build
    now = datetime.now(timezone.utc)
    # Use a timestamp slightly in the future to ensure it's definitely within 0 hours
    recent_timestamp = int((now + timedelta(seconds=1)).timestamp() * 1000)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "very-recent-job",
                "url": "http://jenkins/job/very-recent-job/",
                "lastBuild": {
                    "number": 1,
                    "url": "http://jenkins/job/very-recent-job/1/",
                    "result": "FAILURE",
                    "timestamp": recent_timestamp
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=0)
    
    # With 0 hours, should still find very recent builds
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "very-recent-job"
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_large_hours_value(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with very large hours value."""
    # Mock API response with an old failed build
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "old-failed-job",
                "url": "http://jenkins/job/old-failed-job/",
                "lastBuild": {
                    "number": 1,
                    "url": "http://jenkins/job/old-failed-job/1/",
                    "result": "FAILURE",
                    "timestamp": old_timestamp
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=24*365)  # 1 year
    
    # Should find the old build within the large time window
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "old-failed-job"
    mock_requests_get.assert_called_once()