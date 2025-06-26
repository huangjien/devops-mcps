"""Remaining Jenkins tests that don't fit into specific categories."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import requests
from datetime import datetime, timezone, timedelta
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build
from jenkinsapi.view import View

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_jenkins_get_recent_failed_builds_success(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test successful retrieval of recent failed builds."""
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "failed-job",
                "url": "http://jenkins/job/failed-job/",
                "lastBuild": {
                    "number": 10,
                    "url": "http://jenkins/job/failed-job/10/",
                    "result": "FAILURE",
                    "timestamp": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    assert len(result) == 1
    assert result[0]["name"] == "failed-job"
    assert result[0]["result"] == "FAILURE"
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_request_exception(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with request exception."""
    mock_requests_get.side_effect = requests.exceptions.RequestException("Request failed")

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    assert "error" in result
    assert "Request failed" in result["error"]


def test_jenkins_get_recent_failed_builds_http_error(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    assert "error" in result
    assert "404 Not Found" in result["error"]


def test_jenkins_get_recent_failed_builds_json_decode_error(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with JSON decode error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    assert "error" in result
    assert "Invalid JSON" in result["error"]


def test_jenkins_get_recent_failed_builds_filters_by_time(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test that recent failed builds are filtered by time correctly."""
    now = datetime.now(timezone.utc)
    old_build_time = now - timedelta(hours=10)  # Older than 8 hours
    recent_build_time = now - timedelta(hours=2)  # Within 8 hours

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "old-failed-job",
                "url": "http://jenkins/job/old-failed-job/",
                "lastBuild": {
                    "number": 5,
                    "url": "http://jenkins/job/old-failed-job/5/",
                    "result": "FAILURE",
                    "timestamp": int(old_build_time.timestamp() * 1000)
                }
            },
            {
                "name": "recent-failed-job",
                "url": "http://jenkins/job/recent-failed-job/",
                "lastBuild": {
                    "number": 8,
                    "url": "http://jenkins/job/recent-failed-job/8/",
                    "result": "FAILURE",
                    "timestamp": int(recent_build_time.timestamp() * 1000)
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    # Should only return the recent failed build
    assert len(result) == 1
    assert result[0]["name"] == "recent-failed-job"


def test_jenkins_get_recent_failed_builds_filters_by_result(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test that only failed builds are returned."""
    now = datetime.now(timezone.utc)
    recent_time = now - timedelta(hours=2)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "successful-job",
                "url": "http://jenkins/job/successful-job/",
                "lastBuild": {
                    "number": 5,
                    "url": "http://jenkins/job/successful-job/5/",
                    "result": "SUCCESS",
                    "timestamp": int(recent_time.timestamp() * 1000)
                }
            },
            {
                "name": "failed-job",
                "url": "http://jenkins/job/failed-job/",
                "lastBuild": {
                    "number": 8,
                    "url": "http://jenkins/job/failed-job/8/",
                    "result": "FAILURE",
                    "timestamp": int(recent_time.timestamp() * 1000)
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    # Should only return the failed build
    assert len(result) == 1
    assert result[0]["name"] == "failed-job"
    assert result[0]["result"] == "FAILURE"


def test_jenkins_get_recent_failed_builds_handles_missing_lastbuild(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test handling of jobs without lastBuild data."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jobs": [
            {
                "name": "job-without-builds",
                "url": "http://jenkins/job/job-without-builds/",
                "lastBuild": None
            },
            {
                "name": "job-with-build",
                "url": "http://jenkins/job/job-with-build/",
                "lastBuild": {
                    "number": 1,
                    "url": "http://jenkins/job/job-with-build/1/",
                    "result": "FAILURE",
                    "timestamp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)

    # Should only return the job with a build
    assert len(result) == 1
    assert result[0]["name"] == "job-with-build"


def test_jenkins_module_global_client_state(manage_jenkins_module):
    """Test that the global Jenkins client state is properly managed."""
    # Initially should be None
    assert manage_jenkins_module.j is None

    # After setting a test client
    test_client = MagicMock()
    manage_jenkins_module.set_jenkins_client_for_testing(test_client)
    assert manage_jenkins_module.j is test_client

    # Reset to None
    manage_jenkins_module.set_jenkins_client_for_testing(None)
    assert manage_jenkins_module.j is None


def test_complex_nested_data_structure_conversion(manage_jenkins_module):
    """Test _to_dict with complex nested data structures including Jenkins objects."""
    # Create mock Jenkins objects
    mock_job = MagicMock(spec=Job)
    mock_job.name = "complex-job"
    mock_job.baseurl = "http://jenkins/job/complex-job/"
    mock_job.is_enabled.return_value = True
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.return_value = 15
    mock_job.get_last_build_url = MagicMock()
    mock_job.get_last_build_url.return_value = "http://jenkins/job/complex-job/15/"
    mock_job.get_last_buildurl = MagicMock()
    mock_job.get_last_buildurl.return_value = "http://jenkins/job/complex-job/15/"

    mock_view = MagicMock(spec=View)
    mock_view.name = "test-view"
    mock_view.baseurl = "http://jenkins/view/test-view/"


    # Create complex nested structure
    complex_data = {
        "jenkins_data": {
            "jobs": [mock_job],
            "views": [mock_view],
            "metadata": {
                "nested_list": [
                    {"job": mock_job, "priority": 1},
                    {"job": None, "priority": 2}
                ],
                "config": {
                    "enabled": True,
                    "settings": ["option1", "option2"]
                }
            }
        },
        "simple_data": {
            "string": "test",
            "number": 42,
            "boolean": True,
            "null_value": None,
            "list": [1, 2, 3]
        }
    }

    result = manage_jenkins_module._to_dict(complex_data)

    # Verify the structure is preserved and Jenkins objects are converted
    assert isinstance(result, dict)
    assert "jenkins_data" in result
    assert "simple_data" in result

    # Verify job conversion
    job_dict = result["jenkins_data"]["jobs"][0]
    assert job_dict["name"] == "complex-job"
    assert job_dict["is_enabled"] is True

    # Verify view conversion
    view_dict = result["jenkins_data"]["views"][0]
    assert view_dict["name"] == "test-view"
    assert view_dict["url"] == "http://jenkins/view/test-view/"

    # Verify nested structure
    nested_job = result["jenkins_data"]["metadata"]["nested_list"][0]["job"]
    assert nested_job["name"] == "complex-job"

    # Verify simple data is unchanged
    assert result["simple_data"]["string"] == "test"
    assert result["simple_data"]["number"] == 42
    assert result["simple_data"]["boolean"] is True
    assert result["simple_data"]["null_value"] is None
    assert result["simple_data"]["list"] == [1, 2, 3]
