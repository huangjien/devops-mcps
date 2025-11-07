import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from devops_mcps.utils.jenkins.jenkins_helpers import (
  _get_jenkins_client,
  _get_jenkins_constants,
  _get_to_dict,
  _get_cache,
  check_jenkins_credentials,
)


class TestJenkinsHelpers(unittest.TestCase):
  """Test cases for jenkins_helpers.py functions"""

  def setUp(self):
    """Set up test fixtures"""
    # Clear any existing environment variables
    self.original_env = {}
    for key in ["JENKINS_URL", "JENKINS_USERNAME", "JENKINS_TOKEN"]:
      self.original_env[key] = os.environ.get(key)
      if key in os.environ:
        del os.environ[key]

  def tearDown(self):
    """Clean up after tests"""
    # Restore original environment variables
    for key, value in self.original_env.items():
      if value is not None:
        os.environ[key] = value
      elif key in os.environ:
        del os.environ[key]

  @patch("sys.modules")
  def test_get_jenkins_client_with_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_client when jenkins_api module exists with j attribute"""
    # Mock jenkins_api module with j attribute
    mock_jenkins_api = MagicMock()
    mock_client = MagicMock()
    mock_jenkins_api.j = mock_client
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_client()

    mock_modules.get.assert_called_with("devops_mcps.utils.jenkins.jenkins_api")
    self.assertEqual(result, mock_client)

  @patch("sys.modules")
  def test_get_jenkins_client_without_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_client when jenkins_api module doesn't exist"""
    # Mock no jenkins_api module
    mock_modules.get.return_value = None

    result = _get_jenkins_client()

    # Should return the default _j from jenkins_client (which is None in test environment)
    self.assertIsNone(result)

  @patch("sys.modules")
  def test_get_jenkins_constants_with_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_constants when jenkins_api module exists"""
    # Mock jenkins_api module with constants
    mock_jenkins_api = MagicMock()
    mock_jenkins_api.JENKINS_URL = "http://test-jenkins.com"
    mock_jenkins_api.JENKINS_USER = "test_user"
    mock_jenkins_api.JENKINS_TOKEN = "test_token"
    mock_jenkins_api.LOG_LENGTH = 5000
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_jenkins_constants()

    expected = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
      "LOG_LENGTH": 5000,
    }
    self.assertEqual(result, expected)

  @patch("sys.modules")
  def test_get_jenkins_constants_without_jenkins_api_module(self, mock_modules):
    """Test _get_jenkins_constants when jenkins_api module doesn't exist"""
    # Mock no jenkins_api module
    mock_modules.get.return_value = None

    result = _get_jenkins_constants()

    # Should return the default constants from jenkins_client
    self.assertIn("JENKINS_URL", result)
    self.assertIn("JENKINS_USER", result)
    self.assertIn("JENKINS_TOKEN", result)
    self.assertIn("LOG_LENGTH", result)

  @patch("sys.modules")
  def test_get_to_dict_with_jenkins_api_module(self, mock_modules):
    """Test _get_to_dict when jenkins_api module exists with _to_dict"""
    # Mock jenkins_api module with _to_dict function
    mock_jenkins_api = MagicMock()
    mock_to_dict_func = MagicMock()
    mock_jenkins_api._to_dict = mock_to_dict_func
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_to_dict()

    self.assertEqual(result, mock_to_dict_func)

  @patch("sys.modules")
  def test_get_to_dict_without_jenkins_api_module(self, mock_modules):
    """Test _get_to_dict when jenkins_api module doesn't exist"""
    # Mock no jenkins_api module
    mock_modules.get.return_value = None

    result = _get_to_dict()

    # Should return the default _original_to_dict function
    self.assertIsNotNone(result)

  @patch("sys.modules")
  def test_get_cache_with_jenkins_api_module(self, mock_modules):
    """Test _get_cache when jenkins_api module exists with cache"""
    # Mock jenkins_api module with cache
    mock_jenkins_api = MagicMock()
    mock_cache = MagicMock()
    mock_jenkins_api.cache = mock_cache
    mock_modules.get.return_value = mock_jenkins_api

    result = _get_cache()

    self.assertEqual(result, mock_cache)

  @patch("sys.modules")
  def test_get_cache_without_jenkins_api_module(self, mock_modules):
    """Test _get_cache when jenkins_api module doesn't exist"""
    # Mock no jenkins_api module
    mock_modules.get.return_value = None

    result = _get_cache()

    # Should return the default _cache
    self.assertIsNotNone(result)

  @patch("devops_mcps.utils.jenkins.jenkins_helpers._get_jenkins_constants")
  def test_check_jenkins_credentials_with_all_credentials(self, mock_get_constants):
    """Test check_jenkins_credentials with all required credentials"""
    # Mock constants with all credentials
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    result = check_jenkins_credentials()

    self.assertEqual(result, {})

  @patch("devops_mcps.utils.jenkins.jenkins_helpers._get_jenkins_constants")
  def test_check_jenkins_credentials_missing_url(self, mock_get_constants):
    """Test check_jenkins_credentials with missing JENKINS_URL"""
    # Mock constants with missing URL
    mock_get_constants.return_value = {
      "JENKINS_URL": None,
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }

    result = check_jenkins_credentials()

    expected = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected)

  @patch("devops_mcps.utils.jenkins.jenkins_helpers._get_jenkins_constants")
  def test_check_jenkins_credentials_missing_user(self, mock_get_constants):
    """Test check_jenkins_credentials with missing JENKINS_USER"""
    # Mock constants with missing USER
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": None,
      "JENKINS_TOKEN": "test_token",
    }

    result = check_jenkins_credentials()

    expected = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected)

  @patch("devops_mcps.utils.jenkins.jenkins_helpers._get_jenkins_constants")
  def test_check_jenkins_credentials_missing_token(self, mock_get_constants):
    """Test check_jenkins_credentials with missing JENKINS_TOKEN"""
    # Mock constants with missing TOKEN
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": None,
    }

    result = check_jenkins_credentials()

    expected = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected)

  @patch("devops_mcps.utils.jenkins.jenkins_helpers._get_jenkins_constants")
  def test_check_jenkins_credentials_all_missing(self, mock_get_constants):
    """Test check_jenkins_credentials with all credentials missing"""
    # Mock constants with all missing
    mock_get_constants.return_value = {
      "JENKINS_URL": None,
      "JENKINS_USER": None,
      "JENKINS_TOKEN": None,
    }

    result = check_jenkins_credentials()

    expected = {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
    self.assertEqual(result, expected)


if __name__ == "__main__":
  unittest.main()
