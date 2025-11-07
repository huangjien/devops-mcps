"""Test cases for jenkins_queue_api module."""

import unittest
from unittest.mock import patch, MagicMock
from jenkinsapi.jenkins import JenkinsAPIException

from src.devops_mcps.utils.jenkins.jenkins_queue_api import (
  _get_jenkins_client,
  _get_jenkins_constants,
  _get_to_dict,
  _get_cache,
  jenkins_get_queue,
)


class TestJenkinsQueueApiHelpers(unittest.TestCase):
  """Test cases for helper functions in jenkins_queue_api."""

  def test_get_jenkins_client_with_jenkins_api_module(self):
    """Test _get_jenkins_client when jenkins_api module exists with j attribute"""
    mock_jenkins_api = MagicMock()
    mock_jenkins_api.j = "mocked_jenkins_client"

    with patch(
      "src.devops_mcps.utils.jenkins.jenkins_api", mock_jenkins_api, create=True
    ):
      result = _get_jenkins_client()

    self.assertEqual(result, "mocked_jenkins_client")

  def test_get_jenkins_client_without_jenkins_api_module(self):
    """Test _get_jenkins_client when jenkins_api module doesn't exist"""
    with patch("builtins.__import__", side_effect=ImportError):
      result = _get_jenkins_client()

    # Should return _j which is None in test environment
    self.assertIsNone(result)

  def test_get_jenkins_constants_with_jenkins_api_module(self):
    """Test _get_jenkins_constants when jenkins_api module exists"""
    mock_jenkins_api = MagicMock()
    mock_jenkins_api.JENKINS_URL = "http://test-jenkins.com"
    mock_jenkins_api.JENKINS_USER = "test_user"
    mock_jenkins_api.JENKINS_TOKEN = "test_token"

    with patch(
      "src.devops_mcps.utils.jenkins.jenkins_api", mock_jenkins_api, create=True
    ):
      result = _get_jenkins_constants()

    expected = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }
    self.assertEqual(result, expected)

  def test_get_jenkins_constants_without_jenkins_api_module(self):
    """Test _get_jenkins_constants when jenkins_api module doesn't exist"""
    with patch("builtins.__import__", side_effect=ImportError):
      result = _get_jenkins_constants()

    # Should return the default constants (which are None in test environment)
    expected = {"JENKINS_URL": None, "JENKINS_USER": None, "JENKINS_TOKEN": None}
    self.assertEqual(result, expected)

  def test_get_to_dict_with_jenkins_api_module(self):
    """Test _get_to_dict when jenkins_api module exists with _to_dict"""
    mock_jenkins_api = MagicMock()
    mock_to_dict_func = MagicMock()
    mock_jenkins_api._to_dict = mock_to_dict_func

    with patch(
      "src.devops_mcps.utils.jenkins.jenkins_api", mock_jenkins_api, create=True
    ):
      result = _get_to_dict()

    self.assertEqual(result, mock_to_dict_func)

  def test_get_to_dict_without_jenkins_api_module(self):
    """Test _get_to_dict when jenkins_api module doesn't exist"""
    with patch("builtins.__import__", side_effect=ImportError):
      result = _get_to_dict()

    # Should return the original _to_dict function
    from src.devops_mcps.utils.jenkins.jenkins_converters import (
      _to_dict as original_to_dict,
    )

    self.assertEqual(result, original_to_dict)

  def test_get_cache_with_jenkins_api_module(self):
    """Test _get_cache when jenkins_api module exists with cache"""
    mock_jenkins_api = MagicMock()
    mock_cache = MagicMock()
    mock_jenkins_api.cache = mock_cache

    with patch(
      "src.devops_mcps.utils.jenkins.jenkins_api", mock_jenkins_api, create=True
    ):
      result = _get_cache()

    self.assertEqual(result, mock_cache)

  def test_get_cache_without_jenkins_api_module(self):
    """Test _get_cache when jenkins_api module doesn't exist"""
    with patch("builtins.__import__", side_effect=ImportError):
      result = _get_cache()

    # Should return the original cache
    from src.devops_mcps.cache import cache as original_cache

    self.assertEqual(result, original_cache)


class TestJenkinsGetQueue(unittest.TestCase):
  """Test cases for jenkins_get_queue function."""

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_cached_result(self, mock_get_cache):
    """Test jenkins_get_queue returns cached result when available."""
    # Setup mock cache
    mock_cache = MagicMock()
    cached_result = {"queue_items": [{"id": 1, "task": {"name": "test-job"}}]}
    mock_cache.get.return_value = cached_result
    mock_get_cache.return_value = mock_cache

    result = jenkins_get_queue()

    self.assertEqual(result, cached_result)
    mock_cache.get.assert_called_once_with("jenkins:queue:current")

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_client")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_no_client_no_credentials(
    self, mock_get_cache, mock_get_client, mock_get_constants
  ):
    """Test jenkins_get_queue when no client and no credentials."""
    # Setup mocks
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_get_client.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": None,
      "JENKINS_USER": None,
      "JENKINS_TOKEN": None,
    }

    result = jenkins_get_queue()

    expected_error = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected_error)

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_client")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_no_client_with_credentials(
    self, mock_get_cache, mock_get_client, mock_get_constants
  ):
    """Test jenkins_get_queue when no client but credentials are set."""
    # Setup mocks
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache
    mock_get_client.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    result = jenkins_get_queue()

    expected_error = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected_error)

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_to_dict")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_client")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_success(
    self, mock_get_cache, mock_get_client, mock_get_constants, mock_get_to_dict
  ):
    """Test successful jenkins_get_queue."""
    # Setup mocks
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_jenkins_client = MagicMock()
    mock_queue = MagicMock()
    mock_queue_items = [{"id": 1, "task": {"name": "test-job"}}]
    mock_queue.get_queue_items.return_value = mock_queue_items
    mock_jenkins_client.get_queue.return_value = mock_queue
    mock_get_client.return_value = mock_jenkins_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = MagicMock()
    mock_to_dict.return_value = mock_queue_items
    mock_get_to_dict.return_value = mock_to_dict

    result = jenkins_get_queue()

    expected_result = {"queue_items": mock_queue_items}
    self.assertEqual(result, expected_result)
    mock_cache.set.assert_called_once_with(
      "jenkins:queue:current", expected_result, ttl=60
    )

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_to_dict")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_client")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_jenkins_api_exception(
    self, mock_get_cache, mock_get_client, mock_get_constants, mock_get_to_dict
  ):
    """Test jenkins_get_queue with JenkinsAPIException."""
    # Setup mocks
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_jenkins_client = MagicMock()
    mock_jenkins_client.get_queue.side_effect = JenkinsAPIException("Jenkins API Error")
    mock_get_client.return_value = mock_jenkins_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = MagicMock()
    mock_get_to_dict.return_value = mock_to_dict

    result = jenkins_get_queue()

    expected_error = {"error": "Jenkins API Error: Jenkins API Error"}
    self.assertEqual(result, expected_error)

  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_to_dict")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_constants")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_jenkins_client")
  @patch("src.devops_mcps.utils.jenkins.jenkins_queue_api._get_cache")
  def test_jenkins_get_queue_unexpected_exception(
    self, mock_get_cache, mock_get_client, mock_get_constants, mock_get_to_dict
  ):
    """Test jenkins_get_queue with unexpected exception."""
    # Setup mocks
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_jenkins_client = MagicMock()
    mock_jenkins_client.get_queue.side_effect = Exception("Unexpected error")
    mock_get_client.return_value = mock_jenkins_client

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://jenkins.example.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    mock_to_dict = MagicMock()
    mock_get_to_dict.return_value = mock_to_dict

    result = jenkins_get_queue()

    expected_error = {"error": "An unexpected error occurred: Unexpected error"}
    self.assertEqual(result, expected_error)


if __name__ == "__main__":
  unittest.main()
