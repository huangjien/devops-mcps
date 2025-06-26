#!/usr/bin/env python3

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_jenkins_get_queue_no_client(manage_jenkins_module):
    """Test jenkins_get_queue when Jenkins client is not initialized."""
    # Ensure client is None
    manage_jenkins_module.j = None
    
    result = manage_jenkins_module.jenkins_get_queue()
    
    assert result == {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_success(mock_j, mock_jenkins_api):
    """Test successful retrieval of Jenkins queue."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock queue data
    mock_queue_data = {
        "items": [
            {
                "id": 123,
                "task": {
                    "name": "test-job",
                    "url": "http://jenkins/job/test-job/"
                },
                "why": "Waiting for next available executor",
                "inQueueSince": 1234567890000,
                "buildable": True
            },
            {
                "id": 124,
                "task": {
                    "name": "another-job",
                    "url": "http://jenkins/job/another-job/"
                },
                "why": "Build #1 is already in progress",
                "inQueueSince": 1234567891000,
                "buildable": False
            }
        ]
    }
    
    # Mock the get_queue_info method
    # Mock the queue object and its get_queue_items method
    mock_queue = MagicMock()
    # Create mock queue items that will be converted by _to_dict
    mock_queue_items = []
    for item in mock_queue_data["items"]:
        mock_item = MagicMock()
        # Set attributes directly on the mock
        for key, value in item.items():
            setattr(mock_item, key, value)
        mock_queue_items.append(mock_item)
    mock_queue.get_queue_items.return_value = mock_queue_items
    mock_j.get_queue.return_value = mock_queue
    
    result = jenkins_get_queue()
    
    assert "queue_items" in result
    assert len(result["queue_items"]) == 2
    assert result["queue_items"][0]["id"] == 123
    assert result["queue_items"][0]["task"]["name"] == "test-job"
    assert result["queue_items"][1]["id"] == 124
    assert result["queue_items"][1]["task"]["name"] == "another-job"
    assert result["queue_items"][1]["buildable"] is False
    mock_j.get_queue.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_empty(mock_j, mock_jenkins_api):
    """Test jenkins_get_queue when queue is empty."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock empty queue
    mock_queue_data = {"items": []}
    
    # Mock the queue object and its get_queue_items method
    mock_queue = MagicMock()
    # Create mock queue items that will be converted by _to_dict
    mock_queue_items = []
    for item in mock_queue_data["items"]:
        mock_item = MagicMock()
        # Set attributes directly on the mock
        for key, value in item.items():
            setattr(mock_item, key, value)
        mock_queue_items.append(mock_item)
    mock_queue.get_queue_items.return_value = mock_queue_items
    mock_j.get_queue.return_value = mock_queue
    
    result = jenkins_get_queue()
    
    assert "queue_items" in result
    assert len(result["queue_items"]) == 0
    
    mock_j.get_queue.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_jenkins_api_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_queue with JenkinsAPIException."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock JenkinsAPIException
    mock_j.get_queue.side_effect = JenkinsAPIException("Queue access denied")
    
    result = jenkins_get_queue()
    
    assert "error" in result
    assert "Queue access denied" in result["error"]
    mock_j.get_queue.assert_called_once()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_unexpected_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_queue with unexpected exception."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock unexpected exception
    mock_j.get_queue.side_effect = Exception("Unexpected error")
    
    result = jenkins_get_queue()
    
    assert "error" in result
    assert "Unexpected error" in result["error"]
    mock_j.get_queue.assert_called_once()


@patch("src.devops_mcps.jenkins.cache.set")
@patch("src.devops_mcps.jenkins.cache.get")
@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_with_cache(
    mock_j, mock_cache_get, mock_cache_set, mock_jenkins_api
):
    """Test jenkins_get_queue with caching."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock cache miss first
    mock_cache_get.return_value = None
    
    # Mock queue data
    mock_queue_data = {
        "items": [
            {
                "id": 125,
                "task": {
                    "name": "cached-job",
                    "url": "http://jenkins/job/cached-job/"
                },
                "why": "Waiting for executor",
                "inQueueSince": 1234567892000,
                "buildable": True
            }
        ]
    }
    
    # Mock the queue object and its get_queue_items method
    mock_queue = MagicMock()
    # Create mock queue items that will be converted by _to_dict
    mock_queue_items = []
    for item in mock_queue_data["items"]:
        mock_item = MagicMock()
        # Set attributes directly on the mock
        for key, value in item.items():
            setattr(mock_item, key, value)
        mock_queue_items.append(mock_item)
    mock_queue.get_queue_items.return_value = mock_queue_items
    mock_j.get_queue.return_value = mock_queue
    
    result = jenkins_get_queue()
    
    assert "queue_items" in result
    assert len(result["queue_items"]) == 1
    assert result["queue_items"][0]["task"]["name"] == "cached-job"
    
    mock_j.get_queue.assert_called_once()# Verify cache operations
    mock_cache_get.assert_called_once_with("jenkins:queue:current")
    mock_cache_set.assert_called_once_with("jenkins:queue:current", result, ttl=60)


def test_jenkins_get_queue_client_not_initialized_with_missing_credentials(
    monkeypatch, manage_jenkins_module
):
    """Test jenkins_get_queue when client is not initialized due to missing credentials."""
    # Remove environment variables
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)
    
    # Set client to None
    manage_jenkins_module.j = None
    
    result = manage_jenkins_module.jenkins_get_queue()
    
    assert result == {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }


@patch("src.devops_mcps.jenkins.cache.set")
@patch("src.devops_mcps.jenkins.cache.get")
@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_with_cache_hit(
    mock_j, mock_cache_get, mock_cache_set, mock_jenkins_api
):
    """Test jenkins_get_queue with cache hit."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock cache hit
    cached_data = {
        "queue_items": [
            {
                "id": 126,
                "task": {
                    "name": "cached-hit-job",
                    "url": "http://jenkins/job/cached-hit-job/"
                },
                "why": "From cache",
                "inQueueSince": 1234567893000,
                "buildable": True
            }
        ]
    }
    mock_cache_get.return_value = cached_data
    
    result = jenkins_get_queue()
    
    assert result == cached_data
    assert result["queue_items"][0]["task"]["name"] == "cached-hit-job"
    
    # Verify cache was checked but Jenkins API was not called
    mock_cache_get.assert_called_once_with("jenkins:queue:current")
    mock_cache_set.assert_not_called()
    mock_j.get_queue.assert_not_called()


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_queue_with_complex_queue_items(mock_j, mock_jenkins_api):
    """Test jenkins_get_queue with complex queue items containing various fields."""
    from src.devops_mcps.jenkins import jenkins_get_queue
    
    # Mock complex queue data with various optional fields
    mock_queue_data = {
        "items": [
            {
                "id": 127,
                "task": {
                    "name": "complex-job",
                    "url": "http://jenkins/job/complex-job/",
                    "color": "blue"
                },
                "why": "Waiting for next available executor on 'master'",
                "inQueueSince": 1234567894000,
                "buildable": True,
                "stuck": False,
                "blocked": False,
                "buildableStartMilliseconds": 1234567894500,
                "params": "PARAM1=value1\nPARAM2=value2",
                "actions": [
                    {
                        "_class": "hudson.model.CauseAction",
                        "causes": [
                            {
                                "_class": "hudson.model.Cause$UserIdCause",
                                "shortDescription": "Started by user admin",
                                "userId": "admin",
                                "userName": "admin"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Mock the queue object and its get_queue_items method
    mock_queue = MagicMock()
    # Create mock queue items that will be converted by _to_dict
    mock_queue_items = []
    for item in mock_queue_data["items"]:
        mock_item = MagicMock()
        # Set attributes directly on the mock
        for key, value in item.items():
            setattr(mock_item, key, value)
        mock_queue_items.append(mock_item)
    mock_queue.get_queue_items.return_value = mock_queue_items
    mock_j.get_queue.return_value = mock_queue
    
    result = jenkins_get_queue()
    
    assert "queue_items" in result
    assert len(result["queue_items"]) == 1
    queue_item = result["queue_items"][0]
    assert queue_item["id"] == 127
    assert queue_item["task"]["name"] == "complex-job"
    assert queue_item["stuck"] is False
    assert queue_item["blocked"] is False
    assert "actions" in queue_item
    assert len(queue_item["actions"]) == 1
    mock_j.get_queue.assert_called_once()