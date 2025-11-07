"""Tests for jenkins_job_api module."""

from unittest.mock import Mock, MagicMock, patch
from jenkinsapi.jenkins import JenkinsAPIException

from devops_mcps.utils.jenkins.jenkins_job_api import (
  _get_jenkins_client,
  _get_jenkins_constants,
  _get_to_dict,
  _get_cache,
  jenkins_get_jobs,
)


class TestGetJenkinsClient:
  """Test cases for _get_jenkins_client function."""

  @patch("sys.modules")
  def test_get_jenkins_client_with_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_client when jenkins_api module is available."""
    # Create a mock jenkins_api module with j attribute
    mock_jenkins_api = Mock()
    mock_jenkins_api.j = "test_client"
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_client()
    assert result == "test_client"

  @patch("sys.modules")
  def test_get_jenkins_client_import_error(self, mock_modules):
    """Test _get_jenkins_client when jenkins_api module import fails."""
    # Simulate ImportError by removing the module from sys.modules
    mock_modules.get.return_value = None

    result = _get_jenkins_client()
    # Should return the original _j client
    from devops_mcps.utils.jenkins.jenkins_client import j as _j

    assert result == _j

  @patch("sys.modules")
  def test_get_jenkins_client_attribute_error(self, mock_modules):
    """Test _get_jenkins_client when jenkins_api module lacks 'j' attribute."""
    # Create a mock module without 'j' attribute
    mock_jenkins_api = Mock()
    del mock_jenkins_api.j
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_client()
    # Should return the original _j client
    from devops_mcps.utils.jenkins.jenkins_client import j as _j

    assert result == _j


class TestGetJenkinsConstants:
  """Test cases for _get_jenkins_constants function."""

  @patch("sys.modules")
  def test_get_jenkins_constants_with_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_constants when jenkins_api module is available."""
    expected = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }
    mock_jenkins_api = Mock()
    mock_jenkins_api.JENKINS_URL = expected["JENKINS_URL"]
    mock_jenkins_api.JENKINS_USER = expected["JENKINS_USER"]
    mock_jenkins_api.JENKINS_TOKEN = expected["JENKINS_TOKEN"]
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_constants()
    assert result == expected

  @patch("sys.modules")
  def test_get_jenkins_constants_import_error(self, mock_modules):
    """Test _get_jenkins_constants when jenkins_api module import fails."""
    # Simulate ImportError by removing the module from sys.modules
    mock_modules.get.return_value = None

    result = _get_jenkins_constants()
    expected = {"JENKINS_URL": None, "JENKINS_USER": None, "JENKINS_TOKEN": None}
    assert result == expected

  @patch("sys.modules")
  def test_get_jenkins_constants_attribute_error(self, mock_modules):
    """Test _get_jenkins_constants when jenkins_api module lacks required attributes."""
    # Create a mock module without the constants
    mock_jenkins_api = Mock()
    # Remove attributes to simulate missing constants
    if hasattr(mock_jenkins_api, "JENKINS_URL"):
      del mock_jenkins_api.JENKINS_URL
    if hasattr(mock_jenkins_api, "JENKINS_USER"):
      del mock_jenkins_api.JENKINS_USER
    if hasattr(mock_jenkins_api, "JENKINS_TOKEN"):
      del mock_jenkins_api.JENKINS_TOKEN
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_constants()
    # Should return the fallback constants from jenkins_client
    # In test environment, these are None because no environment variables are set
    expected = {"JENKINS_URL": None, "JENKINS_USER": None, "JENKINS_TOKEN": None}
    assert result == expected


class TestGetToDict:
  """Test cases for _get_to_dict function."""

  @patch("sys.modules")
  def test_get_to_dict_with_jenkins_api_module(self, mock_modules):
    """Test _get_to_dict when jenkins_api module is available."""
    mock_jenkins_api = MagicMock()
    mock_to_dict = MagicMock()
    mock_jenkins_api._to_dict = mock_to_dict
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_to_dict()
    assert result == mock_to_dict

  @patch("sys.modules")
  def test_get_to_dict_import_error(self, mock_modules):
    """Test _get_to_dict when jenkins_api module import fails."""
    # Simulate ImportError by removing the module from sys.modules
    mock_modules.get.return_value = None

    result = _get_to_dict()
    # Should return the original _to_dict function
    from devops_mcps.utils.jenkins.jenkins_converters import (
      _to_dict as _original_to_dict,
    )

    assert result == _original_to_dict

  @patch("sys.modules")
  def test_get_to_dict_attribute_error(self, mock_modules):
    """Test _get_to_dict when jenkins_api module lacks '_to_dict' attribute."""
    # Create a mock module without '_to_dict' attribute
    mock_jenkins_api = Mock()
    del mock_jenkins_api._to_dict
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_to_dict()
    # Should return the original _to_dict function
    from devops_mcps.utils.jenkins.jenkins_converters import (
      _to_dict as _original_to_dict,
    )

    assert result == _original_to_dict


class TestGetCache:
  """Test cases for _get_cache function."""

  @patch("sys.modules")
  def test_get_cache_with_jenkins_api_module(self, mock_modules):
    """Test _get_cache when jenkins_api module is available."""
    mock_jenkins_api = MagicMock()
    mock_cache = MagicMock()
    mock_jenkins_api.cache = mock_cache
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_cache()
    assert result == mock_cache

  @patch("sys.modules")
  def test_get_cache_import_error(self, mock_modules):
    """Test _get_cache when jenkins_api module is not available."""
    mock_modules.get.return_value = None
    result = _get_cache()
    # Should return the original cache object
    from devops_mcps.cache import cache as _cache

    assert result == _cache

  @patch("sys.modules")
  def test_get_cache_attribute_error(self, mock_modules):
    """Test _get_cache when jenkins_api module lacks 'cache' attribute."""
    # Create a mock module without 'cache' attribute
    mock_jenkins_api = Mock()
    del mock_jenkins_api.cache
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_cache()
    # Should return the original cache object
    from devops_mcps.cache import cache as _cache

    assert result == _cache


class TestJenkinsGetJobs:
  """Test cases for jenkins_get_jobs function."""

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_client")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_to_dict")
  def test_jenkins_get_jobs_success(
    self, mock_get_to_dict, mock_get_constants, mock_get_client, mock_get_cache
  ):
    """Test successful jenkins_get_jobs."""
    # Setup mocks
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_client = Mock()
    mock_job1 = Mock()
    mock_job1.name = "job1"
    mock_job2 = Mock()
    mock_job2.name = "job2"
    mock_client.values.return_value = [mock_job1, mock_job2]
    mock_get_client.return_value = mock_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = Mock(side_effect=lambda x: f"dict_{x.name}")
    mock_get_to_dict.return_value = mock_to_dict

    # Execute
    result = jenkins_get_jobs()

    # Verify
    assert result == ["dict_job1", "dict_job2"]
    mock_cache.set.assert_called_once_with(
      "jenkins:jobs:all", ["dict_job1", "dict_job2"], ttl=300
    )

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_client")
  def test_jenkins_get_jobs_client_none(self, mock_get_client, mock_get_cache):
    """Test jenkins_get_jobs when Jenkins client is None."""
    # Setup mocks
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_get_client.return_value = None

    # Execute
    result = jenkins_get_jobs()

    # Verify
    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_client")
  def test_jenkins_get_jobs_client_none_with_valid_constants(
    self, mock_get_client, mock_get_cache, mock_get_constants
  ):
    """Test jenkins_get_jobs when client is None but constants are valid (hits line 92)."""
    # Setup mocks
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    # Mock constants to be valid (not None/empty) to bypass line 88-91 and hit line 92
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "valid_user",
      "JENKINS_TOKEN": "valid_token",
    }

    # Simulate the client being None to hit the second return statement (line 92)
    mock_get_client.return_value = None

    # Execute
    result = jenkins_get_jobs()

    # Verify
    expected = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    assert result == expected

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_client")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_to_dict")
  def test_jenkins_get_jobs_jenkins_api_exception(
    self, mock_get_to_dict, mock_get_constants, mock_get_client, mock_get_cache
  ):
    """Test jenkins_get_jobs with JenkinsAPIException."""
    # Setup mocks
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_client = Mock()
    mock_client.values.side_effect = JenkinsAPIException("API error")
    mock_get_client.return_value = mock_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = Mock()
    mock_get_to_dict.return_value = mock_to_dict

    # Execute
    result = jenkins_get_jobs()

    # Verify
    assert "error" in result
    assert "Jenkins API Error" in result["error"]

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_client")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_to_dict")
  def test_jenkins_get_jobs_general_exception(
    self, mock_get_to_dict, mock_get_constants, mock_get_client, mock_get_cache
  ):
    """Test jenkins_get_jobs with general exception."""
    # Setup mocks
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_client = Mock()
    mock_client.values.side_effect = ValueError("Unexpected error")
    mock_get_client.return_value = mock_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = Mock()
    mock_get_to_dict.return_value = mock_to_dict

    # Execute
    result = jenkins_get_jobs()

    # Verify
    assert "error" in result
    assert "An unexpected error occurred" in result["error"]

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  def test_jenkins_get_jobs_cached_result(self, mock_get_cache):
    """Test jenkins_get_jobs returns cached result."""
    # Setup mocks
    cached_data = [{"name": "cached-job"}]
    mock_cache = Mock()
    mock_cache.get.return_value = cached_data
    mock_get_cache.return_value = mock_cache

    # Execute
    result = jenkins_get_jobs()

    # Verify
    assert result == cached_data
    mock_cache.get.assert_called_once_with("jenkins:jobs:all")