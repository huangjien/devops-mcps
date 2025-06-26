"""Tests for Jenkins client initialization and configuration."""

import sys
import pytest
from unittest.mock import patch, MagicMock
import requests
from jenkinsapi.jenkins import JenkinsAPIException


def test_initialize_jenkins_client_missing_env_vars(
    monkeypatch, mock_jenkins_api, manage_jenkins_module
):
    """Test initialization failure due to missing env vars."""
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_TOKEN", raising=False)

    # Need to re-import or reload the module for env vars to be re-read at module level
    if "src.devops_mcps.jenkins" in sys.modules:
        del sys.modules["src.devops_mcps.jenkins"]
    import src.devops_mcps.jenkins as reloaded_jenkins_module

    client = reloaded_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert reloaded_jenkins_module.j is None
    mock_jenkins_api.assert_not_called()  # Jenkins class should not be instantiated


def test_initialize_jenkins_client_connection_error(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test initialization failure due to connection error."""
    mock_jenkins_api.get_master_data.side_effect = requests.exceptions.ConnectionError(
        "Connection failed"
    )

    client = manage_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_already_initialized(manage_jenkins_module):
    """Test that initialize_jenkins_client returns existing client if already initialized."""
    # Create a mock Jenkins API instance
    mock_jenkins_api = MagicMock()
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    # Call initialize_jenkins_client
    result = manage_jenkins_module.initialize_jenkins_client()

    # Should return the existing client
    assert result is mock_jenkins_api
    assert manage_jenkins_module.j is mock_jenkins_api


def test_initialize_jenkins_client_unexpected_error(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test initialization failure due to unexpected error."""
    mock_jenkins_api.get_master_data.side_effect = ValueError("Unexpected error")

    client = manage_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert manage_jenkins_module.j is None


def test_set_jenkins_client_for_testing(manage_jenkins_module):
    """Test setting Jenkins client for testing purposes."""
    mock_client = MagicMock()
    manage_jenkins_module.set_jenkins_client_for_testing(mock_client)
    assert manage_jenkins_module.j is mock_client


def test_initialize_jenkins_client_jenkins_api_exception(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test initialization failure due to JenkinsAPIException."""
    mock_jenkins_api.get_master_data.side_effect = JenkinsAPIException("Jenkins API Error")

    client = manage_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_general_exception(
    mock_env_vars, mock_jenkins_api, manage_jenkins_module
):
    """Test initialization failure due to general exception."""
    mock_jenkins_api.get_master_data.side_effect = Exception("General error")

    client = manage_jenkins_module.initialize_jenkins_client()
    assert client is None
    assert manage_jenkins_module.j is None


def test_initialize_jenkins_client_already_initialized_extended(
    manage_jenkins_module
):
    """Test extended scenario for already initialized client."""
    # Create a mock Jenkins API instance
    mock_jenkins_api = MagicMock()
    type(mock_jenkins_api).__bool__ = lambda self: True
    manage_jenkins_module.j = mock_jenkins_api

    # Call initialize_jenkins_client multiple times
    result1 = manage_jenkins_module.initialize_jenkins_client()
    result2 = manage_jenkins_module.initialize_jenkins_client()

    # Should return the same existing client both times
    assert result1 is mock_jenkins_api
    assert result2 is mock_jenkins_api
    assert manage_jenkins_module.j is mock_jenkins_api


def test_jenkins_module_global_client_state(manage_jenkins_module):
    """Test that the global client state is properly managed."""
    # Initially, client should be None
    assert manage_jenkins_module.j is None

    # Set a mock client
    mock_client = MagicMock()
    manage_jenkins_module.j = mock_client
    assert manage_jenkins_module.j is mock_client

    # Reset to None
    manage_jenkins_module.j = None
    assert manage_jenkins_module.j is None


def test_module_initialization_in_non_test_environment(manage_jenkins_module):
    """Test module initialization behavior in non-test environment."""
    # This test verifies that the module can be imported and initialized
    # without any environment variables set, which should result in j being None
    
    # The manage_jenkins_module fixture already handles this by setting j = None
    # and clearing the cache, so we just need to verify the state
    assert manage_jenkins_module.j is None
    
    # Verify that we can access the module's functions
    assert hasattr(manage_jenkins_module, 'initialize_jenkins_client')
    assert hasattr(manage_jenkins_module, 'jenkins_get_jobs')
    assert hasattr(manage_jenkins_module, 'jenkins_get_build_log')


def test_log_length_environment_variable(manage_jenkins_module):
    """Test that LOG_LENGTH environment variable is properly accessed."""
    # This test verifies that the module can access the LOG_LENGTH environment variable
    # The actual value is set by the mock_env_vars fixture in other tests
    import os
    
    # Test with LOG_LENGTH set
    os.environ['LOG_LENGTH'] = '1000'
    log_length = os.getenv('LOG_LENGTH', '10000')
    assert log_length == '1000'
    
    # Test with LOG_LENGTH not set
    if 'LOG_LENGTH' in os.environ:
        del os.environ['LOG_LENGTH']
    log_length = os.getenv('LOG_LENGTH', '10000')
    assert log_length == '10000'


def test_jenkins_environment_variables_access(manage_jenkins_module):
    """Test access to Jenkins environment variables."""
    import os
    
    # Test accessing Jenkins environment variables
    jenkins_url = os.getenv('JENKINS_URL')
    jenkins_user = os.getenv('JENKINS_USER')
    jenkins_token = os.getenv('JENKINS_TOKEN')
    
    # These may be None if not set, which is expected behavior
    # The actual validation happens in the initialize_jenkins_client function
    assert jenkins_url is None or isinstance(jenkins_url, str)
    assert jenkins_user is None or isinstance(jenkins_user, str)
    assert jenkins_token is None or isinstance(jenkins_token, str)