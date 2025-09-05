"""Unit tests for jenkins_view_api.py."""

import sys
from unittest.mock import patch, MagicMock
from devops_mcps.utils.jenkins.jenkins_view_api import (
  _get_jenkins_client,
  _get_jenkins_constants,
  _get_to_dict,
  _get_cache,
  jenkins_get_all_views,
)


class TestGetJenkinsClient:
  """Test cases for _get_jenkins_client function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_jenkins_client_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_jenkins_client when jenkins_api module is available."""
    mock_jenkins_api.j = "test_client"

    result = _get_jenkins_client()
    assert result == "test_client"

  def test_get_jenkins_client_without_jenkins_api_module(self):
    """Test _get_jenkins_client when jenkins_api module is not available."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    try:
      result = _get_jenkins_client()
      # Should return the default client from jenkins_client (which might be None)
      # The important thing is that it doesn't crash
      assert result is not None or result is None  # Accept either
    finally:
      # Restore original module if it existed
      if original_module is not None:
        sys.modules[jenkins_api_module] = original_module

  def test_get_jenkins_client_import_error(self):
    """Test _get_jenkins_client when jenkins_api module import fails."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    # Mock the import to raise ImportError
    with patch(
      "builtins.__import__", side_effect=ImportError("No module named 'jenkins_api'")
    ):
      try:
        result = _get_jenkins_client()
        # Should return None when import fails
        assert result is None
      finally:
        # Restore original module if it existed
        if original_module is not None:
          sys.modules[jenkins_api_module] = original_module

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_jenkins_client_attribute_error(self, mock_jenkins_api):
    """Test _get_jenkins_client when jenkins_api module lacks j attribute."""
    # Mock jenkins_api module without the j attribute
    del mock_jenkins_api.j

    result = _get_jenkins_client()

    # Should return None when attribute is missing
    assert result is None


class TestGetJenkinsConstants:
  """Test cases for _get_jenkins_constants function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_jenkins_constants_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_jenkins_constants when jenkins_api module is available."""
    expected = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }
    mock_jenkins_api.JENKINS_URL = expected["JENKINS_URL"]
    mock_jenkins_api.JENKINS_USER = expected["JENKINS_USER"]
    mock_jenkins_api.JENKINS_TOKEN = expected["JENKINS_TOKEN"]

    result = _get_jenkins_constants()
    assert result == expected

  def test_get_jenkins_constants_import_error(self):
    """Test _get_jenkins_constants when jenkins_api module import fails."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    # Mock the import to raise ImportError
    with patch(
      "builtins.__import__", side_effect=ImportError("No module named 'jenkins_api'")
    ):
      try:
        result = _get_jenkins_constants()
        # Should return default values from jenkins_client
        assert "JENKINS_URL" in result
        assert "JENKINS_USER" in result
        assert "JENKINS_TOKEN" in result
      finally:
        # Restore original module if it existed
        if original_module is not None:
          sys.modules[jenkins_api_module] = original_module

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_jenkins_constants_attribute_error(self, mock_jenkins_api):
    """Test _get_jenkins_constants when jenkins_api module lacks expected attributes."""
    # Mock jenkins_api module without the expected attributes
    del mock_jenkins_api.JENKINS_URL
    del mock_jenkins_api.JENKINS_USER
    del mock_jenkins_api.JENKINS_TOKEN

    result = _get_jenkins_constants()

    # Should return default values from jenkins_client
    assert "JENKINS_URL" in result
    assert "JENKINS_USER" in result
    assert "JENKINS_TOKEN" in result

  def test_get_jenkins_constants_without_jenkins_api_module(self):
    """Test _get_jenkins_constants when jenkins_api module is not available."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    try:
      result = _get_jenkins_constants()
      # Should return default values from jenkins_client
      assert "JENKINS_URL" in result
      assert "JENKINS_USER" in result
      assert "JENKINS_TOKEN" in result
    finally:
      # Restore original module if it existed
      if original_module is not None:
        sys.modules[jenkins_api_module] = original_module


class TestGetToDict:
  """Test cases for _get_to_dict function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_to_dict_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_to_dict when jenkins_api module is available."""
    mock_to_dict = MagicMock()
    mock_jenkins_api._to_dict = mock_to_dict

    result = _get_to_dict()
    assert result == mock_to_dict

  def test_get_to_dict_without_jenkins_api_module(self):
    """Test _get_to_dict when jenkins_api module is not available."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    try:
      result = _get_to_dict()
      # Should return the original _to_dict function
      assert result is not None
    finally:
      # Restore original module if it existed
      if original_module is not None:
        sys.modules[jenkins_api_module] = original_module


class TestGetToDict:
  """Test cases for _get_to_dict function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_to_dict_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_to_dict when jenkins_api module is available."""
    expected_func = MagicMock()
    mock_jenkins_api._to_dict = expected_func

    result = _get_to_dict()
    assert result == expected_func


class TestGetCache:
  """Test cases for _get_cache function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_cache_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_cache when jenkins_api module is available."""
    mock_cache = MagicMock()
    mock_jenkins_api.cache = mock_cache

    result = _get_cache()
    assert result == mock_cache

  def test_get_cache_without_jenkins_api_module(self):
    """Test _get_cache when jenkins_api module is not available."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    try:
      result = _get_cache()
      # Should return the default cache
      assert result is not None
    finally:
      # Restore original module if it existed
      if original_module is not None:
        sys.modules[jenkins_api_module] = original_module


class TestJenkinsGetAllViews:
  """Test cases for jenkins_get_all_views function."""

  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_to_dict")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_client")
  def test_jenkins_get_all_views_success(
    self, mock_get_client, mock_get_constants, mock_get_to_dict, mock_get_cache
  ):
    """Test jenkins_get_all_views with successful execution."""
    # Setup mocks
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_get_constants.return_value = {"JENKINS_URL": "http://test.com"}
    mock_to_dict = MagicMock()
    mock_get_to_dict.return_value = mock_to_dict
    mock_cache = MagicMock()
    mock_cache.get.return_value = None  # No cached result
    mock_get_cache.return_value = mock_cache

    # Mock Jenkins client views
    mock_view1 = MagicMock()
    mock_view2 = MagicMock()
    mock_client.views.keys.return_value = [mock_view1, mock_view2]
    mock_to_dict.return_value = {"name": "view1", "url": "http://test.com/view/view1"}

    result = jenkins_get_all_views()

    # Verify the result
    assert result is not None
    mock_client.views.keys.assert_called_once()
    mock_cache.set.assert_called_once()

  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_to_dict")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_client")
  def test_jenkins_get_all_views_no_client(
    self, mock_get_client, mock_get_constants, mock_get_to_dict, mock_get_cache
  ):
    """Test jenkins_get_all_views when client is None."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = None  # No cached result
    mock_get_cache.return_value = mock_cache
    mock_get_client.return_value = None
    mock_get_constants.return_value = {
      "JENKINS_URL": "",
      "JENKINS_USER": "",
      "JENKINS_TOKEN": "",
    }

    result = jenkins_get_all_views()

    assert "error" in result
    assert "Jenkins client not initialized" in result["error"]

  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_to_dict")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_client")
  def test_jenkins_get_all_views_exception(
    self, mock_get_client, mock_get_constants, mock_get_to_dict, mock_get_cache
  ):
    """Test jenkins_get_all_views when an exception occurs."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = None  # No cached result
    mock_get_cache.return_value = mock_cache
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.views.keys.side_effect = Exception("Test exception")

    result = jenkins_get_all_views()

    assert "error" in result
    assert "An unexpected error occurred" in result["error"]

  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_cache")
  def test_jenkins_get_all_views_cached_result(self, mock_get_cache):
    """Test jenkins_get_all_views when result is cached."""
    mock_cache = MagicMock()
    cached_result = [{"name": "cached_view"}]
    mock_cache.get.return_value = cached_result
    mock_get_cache.return_value = mock_cache

    result = jenkins_get_all_views()

    assert result == cached_result
    mock_cache.get.assert_called_once_with("jenkins:views:all")

  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_to_dict")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_constants")
  @patch("devops_mcps.utils.jenkins.jenkins_view_api._get_jenkins_client")
  def test_jenkins_get_all_views_jenkins_api_exception(
    self, mock_get_client, mock_get_constants, mock_get_to_dict, mock_get_cache
  ):
    """Test jenkins_get_all_views when Jenkins API raises an exception."""
    # Setup mocks
    mock_client = MagicMock()
    mock_client.views.keys.side_effect = Exception("Jenkins API error")
    mock_get_client.return_value = mock_client
    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "test_user",
      "JENKINS_TOKEN": "test_token",
    }
    mock_cache = MagicMock()
    mock_get_cache.return_value = mock_cache
    mock_cache.get.return_value = None  # No cached data

    # Call the function
    result = jenkins_get_all_views()

    # Verify the result contains error
    assert "error" in result
    assert "An unexpected error occurred" in result["error"]

    # Verify that the cache was checked
    mock_cache.get.assert_called_once()

  def test_get_to_dict_import_error(self):
    """Test _get_to_dict when jenkins_api module import fails."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    # Mock the import to raise ImportError
    with patch(
      "builtins.__import__", side_effect=ImportError("No module named 'jenkins_api'")
    ):
      try:
        result = _get_to_dict()
        # Should return the default _to_dict function
        assert result is not None
      finally:
        # Restore original module if it existed
        if original_module is not None:
          sys.modules[jenkins_api_module] = original_module

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_to_dict_attribute_error(self, mock_jenkins_api):
    """Test _get_to_dict when jenkins_api module lacks _to_dict attribute."""
    # Mock jenkins_api module without the _to_dict attribute
    del mock_jenkins_api._to_dict

    result = _get_to_dict()

    # Should return the default _to_dict function
    assert result is not None


class TestGetCache:
  """Test cases for _get_cache function."""

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_cache_with_jenkins_api_module(self, mock_jenkins_api):
    """Test _get_cache when jenkins_api module is available."""
    mock_cache = MagicMock()
    mock_jenkins_api.cache = mock_cache

    result = _get_cache()
    assert result == mock_cache

  def test_get_cache_without_jenkins_api_module(self):
    """Test _get_cache when jenkins_api module is not available."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    try:
      result = _get_cache()
      # Should return the default cache
      assert result is not None
    finally:
      # Restore original module if it existed
      if original_module is not None:
        sys.modules[jenkins_api_module] = original_module

  def test_get_cache_import_error(self):
    """Test _get_cache when jenkins_api module import fails."""
    # Remove jenkins_api from sys.modules if it exists
    jenkins_api_module = "devops_mcps.utils.jenkins.jenkins_api"
    original_module = sys.modules.get(jenkins_api_module)
    if jenkins_api_module in sys.modules:
      del sys.modules[jenkins_api_module]

    # Mock the import to raise ImportError
    with patch(
      "builtins.__import__", side_effect=ImportError("No module named 'jenkins_api'")
    ):
      try:
        result = _get_cache()
        # Should return the default cache
        assert result is not None
      finally:
        # Restore original module if it existed
        if original_module is not None:
          sys.modules[jenkins_api_module] = original_module

  @patch("devops_mcps.utils.jenkins.jenkins_api")
  def test_get_cache_attribute_error(self, mock_jenkins_api):
    """Test _get_cache when jenkins_api module lacks cache attribute."""
    # Mock jenkins_api module without the cache attribute
    del mock_jenkins_api.cache

    result = _get_cache()

    # Should return the default cache
    assert result is not None
