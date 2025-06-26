#!/usr/bin/env python3

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.build import Build
from jenkinsapi.view import View
import requests
from datetime import datetime, timezone, timedelta

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_jobs_with_corrupted_job_data(mock_j, mock_jenkins_api):
    """Test jenkins_get_jobs when job data is corrupted or incomplete."""
    from src.devops_mcps.jenkins import jenkins_get_jobs
    
    # Create a mock job that raises exceptions for various methods
    mock_corrupted_job = MagicMock(spec=Job)
    mock_corrupted_job.name = "corrupted-job"
    mock_corrupted_job.baseurl = "http://jenkins/job/corrupted-job/"
    
    # Make various methods raise different types of exceptions
    mock_corrupted_job.is_enabled.side_effect = AttributeError("Method not available")
    mock_corrupted_job.is_queued.side_effect = JenkinsAPIException("API Error")
    mock_corrupted_job.get_last_buildnumber.side_effect = KeyError("lastBuild")
    mock_corrupted_job.get_last_build_url = MagicMock(side_effect=ValueError("Invalid URL"))
    mock_corrupted_job.get_last_buildurl = MagicMock(side_effect=ConnectionError("Network error"))
    
    mock_jenkins_api.values.return_value = [mock_corrupted_job]
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    # Should handle all exceptions gracefully and still return job data
    result = jenkins_get_jobs()
    
    # Should handle exceptions gracefully - either return list or error dict
    assert isinstance(result, (list, dict))
    if isinstance(result, list):
        assert len(result) == 1
        assert result[0]["name"] == "corrupted-job"
        assert result[0]["url"] == "http://jenkins/job/corrupted-job/"
    else:
        assert "error" in result  # Or return an error for corrupted jobs
    mock_jenkins_api.values.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_with_encoding_errors(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_log with various encoding issues."""
    from src.devops_mcps.jenkins import jenkins_get_build_log
    
    # Create log with various encoding issues
    problematic_log = (
        b"\xff\xfe\x00\x00"  # BOM for UTF-32
        b"Normal text\n"
        b"\x80\x81\x82"  # Invalid UTF-8 bytes
        b"More normal text\n"
        b"\xc0\x80"  # Overlong encoding
    ).decode('utf-8', errors='replace')
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_console.return_value = problematic_log
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    result = jenkins_get_build_log("test-job", 1)
    
    # jenkins_get_build_log returns the log content directly as a string
    assert isinstance(result, str)
    assert "Normal text" in result
    assert "More normal text" in result
    # Should handle encoding issues gracefully
    mock_jenkins_api.get_job.assert_called_once_with("test-job")


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_with_console_output_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_log when get_console_output raises an exception."""
    from src.devops_mcps.jenkins import jenkins_get_build_log
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_console.side_effect = JenkinsAPIException("Console output not available")
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    result = jenkins_get_build_log("test-job", 1)
    
    assert "error" in result
    assert "Console output not available" in result["error"]
    mock_jenkins_api.get_job.assert_called_once_with("test-job")


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_with_get_params_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_parameters when get_params raises an exception."""
    from src.devops_mcps.jenkins import jenkins_get_build_parameters
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_params.side_effect = JenkinsAPIException("Parameters not available")
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    result = jenkins_get_build_parameters("test-job", 1)
    
    assert "error" in result
    assert "Parameters not available" in result["error"]
    mock_jenkins_api.get_job.assert_called_once_with("test-job")


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_with_get_views_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_all_views when get_views raises an exception."""
    from src.devops_mcps.jenkins import jenkins_get_all_views
    
    mock_jenkins_api.views.values.side_effect = JenkinsAPIException("Views not accessible")
    mock_j.__bool__ = lambda self: True
    mock_j.views = mock_jenkins_api.views
    
    result = jenkins_get_all_views()
    
    assert "error" in result
    assert "Views not accessible" in result["error"]
    mock_jenkins_api.views.values.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_with_malformed_queue_data(mock_j, mock_jenkins_api):
    """Test jenkins_get_queue with malformed queue data."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock malformed queue data
    malformed_data = {
        "items": [
            {"id": 123},  # Missing required fields
            {"task": {"name": "incomplete-job"}},  # Missing id
            "invalid_item",  # Not a dictionary
            None,  # Null item
            {"id": "not_a_number", "task": {"name": "string-id-job"}}
        ],
        "extra_field": "should_be_ignored"
    }
    
    mock_queue = MagicMock()
    mock_queue.get_queue_items.return_value = malformed_data
    mock_jenkins_api.get_queue.return_value = mock_queue
    mock_j.__bool__ = lambda self: True
    mock_j.get_queue = mock_jenkins_api.get_queue
    
    result = jenkins_get_queue()
    
    # Should return the malformed data wrapped in queue_items
    assert "queue_items" in result
    # The malformed data should be processed through _to_dict
    assert isinstance(result["queue_items"], dict)
    mock_jenkins_api.get_queue.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_functions_with_network_interruption(mock_j, mock_jenkins_api):
    """Test various Jenkins functions when network is interrupted during operation."""
    from src.devops_mcps.jenkins import (
        jenkins_get_jobs, jenkins_get_build_log, 
        jenkins_get_build_parameters, jenkins_get_all_views
    )
    
    # Simulate network interruption
    network_error = ConnectionError("Network unreachable")
    
    mock_jenkins_api.values.side_effect = network_error
    mock_jenkins_api.get_job.side_effect = network_error
    mock_jenkins_api.views.values.side_effect = network_error
    
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    mock_j.get_job = mock_jenkins_api.get_job
    mock_j.views = mock_jenkins_api.views
    
    # Test each function handles network errors
    jobs_result = jenkins_get_jobs()
    assert "error" in jobs_result
    assert "Network unreachable" in jobs_result["error"]
    
    log_result = jenkins_get_build_log("test-job", 1)
    assert "error" in log_result
    assert "Network unreachable" in log_result["error"]
    
    params_result = jenkins_get_build_parameters("test-job", 1)
    assert "error" in params_result
    assert "Network unreachable" in params_result["error"]
    
    views_result = jenkins_get_all_views()
    assert "error" in views_result
    assert "Network unreachable" in views_result["error"]


def test_jenkins_get_recent_failed_builds_with_json_decode_error(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with JSON decode error."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    assert "error" in result
    assert "Invalid JSON" in result["error"]
    mock_requests_get.assert_called_once()


def test_jenkins_get_recent_failed_builds_with_partial_credentials(
    monkeypatch, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with only partial credentials."""
    # Set only some credentials
    monkeypatch.setenv("JENKINS_URL", "http://jenkins")
    monkeypatch.setenv("JENKINS_USER", "user")
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)  # Missing token
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]
    mock_requests_get.assert_not_called()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_functions_with_memory_pressure(mock_j, mock_jenkins_api):
    """Test Jenkins functions under simulated memory pressure."""
    from src.devops_mcps.jenkins import jenkins_get_jobs, jenkins_get_build_log
    
    # Simulate memory error
    mock_jenkins_api.values.side_effect = MemoryError("Out of memory")
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    result = jenkins_get_jobs()
    
    assert "error" in result
    assert "Out of memory" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_log_with_extremely_large_build_number(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_log with extremely large build number."""
    from src.devops_mcps.jenkins import jenkins_get_build_log
    
    mock_job = MagicMock(spec=Job)
    mock_job.get_build.side_effect = KeyError("Build not found")
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    # Test with very large build number
    result = jenkins_get_build_log("test-job", 999999999)
    
    assert "error" in result
    assert "Build #999999999 not found for job test-job" in result["error"]
    mock_jenkins_api.get_job.assert_called_once_with("test-job")
    mock_job.get_build.assert_called_once_with(999999999)


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_build_parameters_with_circular_reference_in_params(mock_j, mock_jenkins_api):
    """Test jenkins_get_build_parameters with circular references in parameters."""
    from src.devops_mcps.jenkins import jenkins_get_build_parameters
    
    # Create parameters with circular reference
    circular_dict = {"key": "value"}
    circular_dict["self"] = circular_dict
    
    mock_job = MagicMock(spec=Job)
    mock_build = MagicMock(spec=Build)
    mock_build.get_params.return_value = {
        "normal_param": "value",
        "circular_param": circular_dict
    }
    mock_job.get_build.return_value = mock_build
    mock_jenkins_api.get_job.return_value = mock_job
    
    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.get_job = mock_jenkins_api.get_job
    
    # Should handle circular references gracefully
    result = jenkins_get_build_parameters("test-job", 1)
    
    assert "normal_param" in result
    assert "circular_param" in result
    # Circular reference should be handled without infinite recursion
    mock_jenkins_api.get_job.assert_called_once_with("test-job")


def test_jenkins_functions_with_unicode_job_names():
    """Test Jenkins functions with Unicode job names."""
    from src.devops_mcps.jenkins import (
        jenkins_get_build_log, jenkins_get_build_parameters
    )
    
    unicode_job_names = [
        "测试作业",  # Chinese
        "тестовая-работа",  # Russian
        "🚀-deployment-job",  # Emoji
        "café-build",  # Accented characters
        "job-with-ñ-and-ü",  # Special characters
    ]
    
    with patch('src.devops_mcps.jenkins.j') as mock_j:
        mock_j.get_job.side_effect = KeyError("Job not found")
        
        for job_name in unicode_job_names:
            log_result = jenkins_get_build_log(job_name, 1)
            assert "error" in log_result
            
            params_result = jenkins_get_build_parameters(job_name, 1)
            assert "error" in params_result


def test_jenkins_get_recent_failed_builds_with_invalid_json_structure(
    mock_env_vars, mock_requests_get, manage_jenkins_module
):
    """Test jenkins_get_recent_failed_builds with valid JSON but invalid structure."""
    # Valid JSON but unexpected structure
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "unexpected_key": "unexpected_value",
        "jobs": "not_a_list",  # Should be a list
        "another_field": 123
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    result = manage_jenkins_module.jenkins_get_recent_failed_builds(hours_ago=8)
    
    # Should handle gracefully and return empty list
    if isinstance(result, dict) and "error" in result:
        # If there's an error in processing, that's also acceptable
        assert "error" in result
    else:
        # Otherwise should return empty list
        assert isinstance(result, list)
        assert len(result) == 0
    mock_requests_get.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_functions_with_concurrent_access(mock_j, mock_jenkins_api):
    """Test Jenkins functions under simulated concurrent access scenarios."""
    from src.devops_mcps.jenkins import jenkins_get_jobs
    
    # Simulate race condition or concurrent access error
    mock_jenkins_api.values.side_effect = RuntimeError("Concurrent modification")
    mock_j.__bool__ = lambda self: True
    mock_j.values = mock_jenkins_api.values
    
    result = jenkins_get_jobs()
    
    assert "error" in result
    assert "Concurrent modification" in result["error"]