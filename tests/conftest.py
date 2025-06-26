"""Shared test fixtures and utilities for the devops-mcps test suite."""

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

# --- Jenkins Test Fixtures ---

@pytest.fixture(autouse=True)
def manage_jenkins_module():
    """Fixture to manage the jenkins module import and cleanup."""
    if "src.devops_mcps.jenkins" in sys.modules:
        del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as jenkins_module

    jenkins_module.j = None
    # Clear cache before each test
    from src.devops_mcps.cache import cache
    cache.clear()
    yield jenkins_module
    # Do not reset j after yield; allow tests to control client state


@pytest.fixture
def mock_jenkins_api():
    """Mocks the jenkinsapi.Jenkins class."""
    with patch("jenkinsapi.jenkins.Jenkins") as mock_jenkins:
        # Mock the instance methods/properties needed
        mock_instance = mock_jenkins.return_value
        mock_instance.get_master_data.return_value = {
            "nodeName": "master"
        }  # Simulate successful connection
        mock_instance.keys.return_value = []  # Default to no jobs
        mock_instance.values.return_value = []  # Default to no job objects
        mock_instance.views.keys.return_value = []  # Default to no views
        mock_instance.views.values.return_value = []  # Default to no view objects
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


# --- GitHub Test Fixtures ---

@pytest.fixture
def mock_github_env_vars(monkeypatch):
    """Set up mock environment variables for GitHub client."""
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
    yield


@pytest.fixture
def mock_github():
    with patch("devops_mcps.github.Github") as mock:
        yield mock


@pytest.fixture
def mock_github_api(mock_github_env_vars):
    """Mock GitHub API and initialize client."""
    with patch("devops_mcps.github.Github", autospec=True) as mock_github:
        mock_instance = mock_github.return_value
        mock_instance.get_user.return_value = MagicMock(login="test_user")
        mock_instance.get_rate_limit.return_value = MagicMock()
        mock_instance.get_repo.return_value = MagicMock()

        # Patch the global client directly
        with patch("devops_mcps.github.g", new=mock_instance):
            yield mock_instance


# --- Cache Test Fixtures ---

@pytest.fixture
def cache():
    """Provides a fresh cache instance for testing."""
    from devops_mcps.cache import cache
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    with patch("devops_mcps.cache.cache") as mock:
        yield mock


# --- Logger Test Fixtures ---

@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch("devops_mcps.logger.logger") as mock:
        yield mock


@pytest.fixture
def mock_cache_get():
    """Mocks cache.get method."""
    with patch("devops_mcps.cache.cache.get") as mock:
        yield mock


@pytest.fixture
def mock_cache_set():
    """Mocks cache.set method."""
    with patch("devops_mcps.cache.cache.set") as mock:
        yield mock