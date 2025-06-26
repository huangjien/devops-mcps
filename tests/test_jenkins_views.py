"""Tests for Jenkins view operations."""

import pytest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException
from jenkinsapi.view import View


def test_jenkins_get_all_views_no_client(manage_jenkins_module):
    """Test jenkins_get_all_views when client is not initialized."""
    manage_jenkins_module.j = None  # Ensure client is None
    result = manage_jenkins_module.jenkins_get_all_views()
    assert result == {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }


def test_jenkins_get_all_views_success(mock_env_vars, mock_jenkins_api, manage_jenkins_module):
    """Test successful retrieval of all views."""
    from jenkinsapi.view import View

    # Setup mock view
    mock_view = MagicMock(spec=View)
    mock_view.name = "TestView"
    mock_view.baseurl = "http://jenkins/view/TestView/"

    mock_jenkins_api.views.values.return_value = [mock_view]
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_all_views()

    assert len(result) == 1
    assert result[0]["name"] == "TestView"
    assert result[0]["url"] == "http://jenkins/view/TestView/"


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_jenkins_api_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_all_views with JenkinsAPIException."""
    from jenkinsapi.custom_exceptions import JenkinsAPIException

    mock_jenkins_api.views.values.side_effect = JenkinsAPIException("API Error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.views = mock_jenkins_api.views

    from src.devops_mcps.jenkins import jenkins_get_all_views

    result = jenkins_get_all_views()

    assert "error" in result
    assert "Jenkins API Error" in result["error"]


@patch("src.devops_mcps.jenkins.j")
def test_jenkins_get_all_views_unexpected_exception(mock_j, mock_jenkins_api):
    """Test jenkins_get_all_views with unexpected exception."""
    mock_jenkins_api.views.values.side_effect = ValueError("Unexpected error")

    # Replace the mock with our jenkins api mock
    mock_j.__bool__ = lambda self: True
    mock_j.views = mock_jenkins_api.views

    from src.devops_mcps.jenkins import jenkins_get_all_views

    result = jenkins_get_all_views()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


def test_jenkins_get_all_views_with_cache(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_all_views with caching."""
    from src.devops_mcps.cache import cache
    from jenkinsapi.view import View

    # Setup mock view
    mock_view = MagicMock(spec=View)
    mock_view.name = "TestView"
    mock_view.baseurl = "http://jenkins/view/TestView/"

    mock_jenkins_api.views.values.return_value = [mock_view]
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    # First call should cache the result
    result1 = manage_jenkins_module.jenkins_get_all_views()
    assert len(result1) == 1
    assert result1[0]["name"] == "TestView"

    # Verify result is cached
    cached_result = cache.get("jenkins:views:all")
    assert cached_result is not None


def test_jenkins_get_all_views_client_not_initialized_with_missing_credentials(
    monkeypatch, manage_jenkins_module
):
    """Test jenkins_get_all_views when client is not initialized due to missing credentials."""
    # Remove environment variables
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)

    # Ensure client is None
    manage_jenkins_module.j = None

    result = manage_jenkins_module.jenkins_get_all_views()
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]


def test_jenkins_get_all_views_with_cache_hit(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_all_views with cache hit."""
    from src.devops_mcps.cache import cache

    # Initialize Jenkins client
    manage_jenkins_module.j = mock_jenkins_api

    # Pre-populate cache
    cached_views = [{"name": "CachedView", "url": "http://jenkins/view/CachedView/"}]
    cache.set("jenkins:views:all", cached_views, ttl=300)

    # Call should return cached result without hitting Jenkins API
    result = manage_jenkins_module.jenkins_get_all_views()
    assert result == cached_views


def test_jenkins_get_all_views_with_values_method(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test jenkins_get_all_views using views.values() method."""
    from jenkinsapi.view import View
    
    # Setup mock views
    mock_view1 = MagicMock(spec=View)
    mock_view1.name = "View1"
    mock_view1.baseurl = "http://jenkins/view/View1/"

    mock_view2 = MagicMock(spec=View)
    mock_view2.name = "View2"
    mock_view2.baseurl = "http://jenkins/view/View2/"

    # Mock the views.values() method to return view objects
    mock_jenkins_api.views.values.return_value = [mock_view1, mock_view2]
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    result = manage_jenkins_module.jenkins_get_all_views()

    assert len(result) == 2
    assert result[0]["name"] == "View1"
    assert result[0]["url"] == "http://jenkins/view/View1/"

    assert result[1]["name"] == "View2"
    assert result[1]["url"] == "http://jenkins/view/View2/"