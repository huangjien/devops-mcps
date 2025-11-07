import os
import unittest
from unittest.mock import patch, MagicMock
import requests

from devops_mcps.artifactory import (
  artifactory_list_items,
  artifactory_search_items,
  artifactory_get_item_info,
)
from devops_mcps.utils.artifactory.artifactory_auth import (
  get_auth as _get_auth,
  validate_artifactory_config as _validate_artifactory_config,
)


class TestArtifactoryAuth(unittest.TestCase):
  """Tests for Artifactory authentication functions."""

  @patch.dict(os.environ, {"ARTIFACTORY_IDENTITY_TOKEN": "test-token"}, clear=True)
  def test_get_auth_with_token(self):
    """Test _get_auth with identity token."""
    auth = _get_auth()
    self.assertEqual(auth, {"Authorization": "Bearer test-token"})

  @patch.dict(
    os.environ,
    {"ARTIFACTORY_USERNAME": "test-user", "ARTIFACTORY_PASSWORD": "test-pass"},
    clear=True,
  )
  def test_get_auth_with_username_password(self):
    """Test _get_auth with username and password."""
    auth = _get_auth()
    self.assertEqual(auth, ("test-user", "test-pass"))

  @patch.dict(os.environ, {}, clear=True)
  def test_get_auth_with_no_credentials(self):
    """Test _get_auth with no credentials."""
    auth = _get_auth()
    self.assertIsNone(auth)

  @patch.dict(
    os.environ, {"ARTIFACTORY_URL": "https://artifactory.example.com"}, clear=True
  )
  def test_validate_config_missing_auth(self):
    """Test _validate_artifactory_config with missing auth."""
    result = _validate_artifactory_config()
    self.assertIsInstance(result, dict)
    self.assertIn("error", result)
    self.assertIn("ARTIFACTORY_IDENTITY_TOKEN", result["error"])

  @patch.dict(
    os.environ,
    {"ARTIFACTORY_USERNAME": "test-user", "ARTIFACTORY_PASSWORD": "test-pass"},
    clear=True,
  )
  def test_validate_config_missing_url(self):
    """Test _validate_artifactory_config with missing URL."""
    result = _validate_artifactory_config()
    self.assertIsInstance(result, dict)
    self.assertIn("error", result)
    self.assertIn("ARTIFACTORY_URL", result["error"])

  @patch.dict(
    os.environ,
    {
      "ARTIFACTORY_URL": "https://artifactory.example.com",
      "ARTIFACTORY_USERNAME": "test-user",
      "ARTIFACTORY_PASSWORD": "test-pass",
    },
    clear=True,
  )
  def test_validate_config_valid(self):
    """Test _validate_artifactory_config with valid config."""
    self.assertTrue(_validate_artifactory_config())


class TestArtifactoryListItems(unittest.TestCase):
  """Tests for artifactory_list_items function."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_list_items_invalid_config(self, mock_validate):
    """Test list_items with invalid config."""
    mock_validate.return_value = {
      "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
    }
    result = artifactory_list_items("repo", "/path")
    self.assertEqual(
      result,
      {
        "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
      },
    )

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_list_items_directory(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items for a directory."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock response for a directory
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "children": [
        {"uri": "/item1", "folder": False},
        {"uri": "/item2", "folder": True},
      ]
    }
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/test-path")

    # Assertions
    self.assertEqual(
      result, [{"uri": "/item1", "folder": False}, {"uri": "/item2", "folder": True}]
    )
    mock_get.assert_called_once()
    self.assertTrue("api/storage/test-repo/test-path" in mock_get.call_args[0][0])
    mock_cache_set.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_list_items_file(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items for a file."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock response for a file
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "uri": "/test-file",
      "created": "2023-01-01T00:00:00Z",
      "size": 1024,
    }
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/test-file")

    # Assertions
    self.assertEqual(
      result, {"uri": "/test-file", "created": "2023-01-01T00:00:00Z", "size": 1024}
    )
    mock_get.assert_called_once()
    mock_cache_set.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_error(self, mock_cache_get, mock_get, mock_auth, mock_validate):
    """Test list_items with API error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/not-found")

    # Assertions
    self.assertTrue("error" in result)
    self.assertTrue("404" in result["error"])
    mock_get.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_from_cache(self, mock_cache_get, mock_validate):
    """Test list_items retrieving from cache."""
    # Setup mocks
    mock_validate.return_value = True
    cached_result = [{"uri": "/cached-item", "folder": False}]
    mock_cache_get.return_value = cached_result

    # Call function
    result = artifactory_list_items("test-repo", "/cached-path")

    # Assertions
    self.assertEqual(result, cached_result)


class TestArtifactorySearchItems(unittest.TestCase):
  """Tests for artifactory_search_items function."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_search_items_invalid_config(self, mock_validate):
    """Test search_items with invalid config."""
    mock_validate.return_value = {
      "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
    }
    result = artifactory_search_items("query")
    self.assertEqual(
      result,
      {
        "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
      },
    )

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_search_items_success(
    self, mock_cache_set, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with successful response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "results": [
        {"name": "item1", "repo": "repo1", "path": "path/to/item1"},
        {"name": "item2", "repo": "repo2", "path": "path/to/item2"},
      ]
    }
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query", ["repo1", "repo2"])

    # Assertions
    self.assertEqual(
      result,
      [
        {"name": "item1", "repo": "repo1", "path": "path/to/item1"},
        {"name": "item2", "repo": "repo2", "path": "path/to/item2"},
      ],
    )
    mock_post.assert_called_once()
    self.assertTrue("api/search/aql" in mock_post.call_args[0][0])
    self.assertTrue("test-query" in mock_post.call_args[1]["data"])
    self.assertTrue("repo1" in mock_post.call_args[1]["data"])
    self.assertTrue("repo2" in mock_post.call_args[1]["data"])
    mock_cache_set.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_error(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with API error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("invalid query")

    # Assertions
    self.assertTrue("error" in result)
    self.assertTrue("400" in result["error"])
    mock_post.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_from_cache(self, mock_cache_get, mock_validate):
    """Test search_items retrieving from cache."""
    # Setup mocks
    mock_validate.return_value = True
    cached_result = [{"name": "cached-item", "repo": "repo", "path": "path"}]
    mock_cache_get.return_value = cached_result

    # Call function
    result = artifactory_search_items("cached-query")

    # Assertions
    self.assertEqual(result, cached_result)


class TestArtifactoryGetItemInfo(unittest.TestCase):
  """Tests for artifactory_get_item_info function."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_get_item_info_invalid_config(self, mock_validate):
    """Test get_item_info with invalid config."""
    mock_validate.return_value = {
      "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
    }
    result = artifactory_get_item_info("repo", "/path")
    self.assertEqual(
      result,
      {
        "error": "Artifactory authentication not configured. Please set either ARTIFACTORY_IDENTITY_TOKEN or both ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD environment variables."
      },
    )

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_get_item_info_directory(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info for a directory."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock response for a directory
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "uri": "/test-dir",
      "created": "2023-01-01T00:00:00Z",
      "children": [
        {"uri": "/test-dir/item1", "folder": False},
        {"uri": "/test-dir/item2", "folder": True},
      ],
    }
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/test-dir")

    # Assertions
    self.assertEqual(
      result,
      {
        "uri": "/test-dir",
        "created": "2023-01-01T00:00:00Z",
        "children": [
          {"uri": "/test-dir/item1", "folder": False},
          {"uri": "/test-dir/item2", "folder": True},
        ],
      },
    )
    mock_get.assert_called_once()
    self.assertTrue("api/storage/test-repo/test-dir" in mock_get.call_args[0][0])
    mock_cache_set.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_get_item_info_file_with_properties(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info for a file with properties."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock responses
    file_response = MagicMock()
    file_response.status_code = 200
    file_response.json.return_value = {
      "uri": "/test-file",
      "created": "2023-01-01T00:00:00Z",
      "size": 1024,
    }

    props_response = MagicMock()
    props_response.status_code = 200
    props_response.json.return_value = {
      "properties": {"prop1": ["value1"], "prop2": ["value2"]}
    }

    # Configure mock_get to return different responses
    mock_get.side_effect = [file_response, props_response]

    # Call function
    result = artifactory_get_item_info("test-repo", "/test-file")

    # Assertions
    self.assertEqual(
      result,
      {
        "uri": "/test-file",
        "created": "2023-01-01T00:00:00Z",
        "size": 1024,
        "properties": {"prop1": ["value1"], "prop2": ["value2"]},
      },
    )
    self.assertEqual(mock_get.call_count, 2)
    self.assertTrue("properties" in mock_get.call_args[0][0])
    mock_cache_set.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with API error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/not-found")

    # Assertions
    self.assertTrue("error" in result)
    self.assertTrue("404" in result["error"])
    mock_get.assert_called_once()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_from_cache(self, mock_cache_get, mock_validate):
    """Test get_item_info retrieving from cache."""
    # Setup mocks
    mock_validate.return_value = True
    cached_result = {"uri": "/cached-item", "size": 1024}
    mock_cache_get.return_value = cached_result

    # Call function
    result = artifactory_get_item_info("test-repo", "/cached-item")

    # Assertions
    self.assertEqual(result, cached_result)


class TestArtifactoryErrorHandling(unittest.TestCase):
  """Tests for error handling in Artifactory API functions."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_401_unauthorized(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with 401 Unauthorized response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 401 response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/unauthorized")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("401", result["error"])
    self.assertIn("unauthorized", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_403_forbidden(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with 403 Forbidden response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock 403 response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/forbidden")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("403", result["error"])
    self.assertIn("forbidden", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_404_not_found(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with 404 Not Found response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/not-found")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("404", result["error"])
    self.assertIn("not found", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_500_server_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with 500 Internal Server Error response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock 500 response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/server-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("500", result["error"])
    self.assertIn("internal server error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_401_unauthorized(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with 401 Unauthorized response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 401 response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("401", result["error"])
    self.assertIn("unauthorized", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_http_error_exception(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with HTTPError exception."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock HTTPError exception
    mock_post.side_effect = requests.exceptions.HTTPError("HTTP Error occurred")

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_request_exception(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with RequestException."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock RequestException
    mock_get.side_effect = requests.exceptions.RequestException("Request failed")

    # Call function
    result = artifactory_get_item_info("test-repo", "/request-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_ssl_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with SSL error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock SSL error
    mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")

    # Call function
    result = artifactory_get_item_info("test-repo", "/ssl-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_401_unauthorized(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with 401 Unauthorized response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 401 response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/unauthorized")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("401", result["error"])
    self.assertIn("unauthorized", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_403_forbidden(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with 403 Forbidden response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock 403 response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/forbidden")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("403", result["error"])
    self.assertIn("forbidden", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_500_server_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with 500 Internal Server Error response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 500 response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/server-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("500", result["error"])
    self.assertIn("internal server error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_403_forbidden(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with 403 Forbidden response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock 403 response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("403", result["error"])
    self.assertIn("forbidden", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_404_not_found(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with 404 Not Found response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("404", result["error"])
    self.assertIn("not found", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_500_server_error(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with 500 Internal Server Error response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock 500 response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("500", result["error"])
    self.assertIn("internal server error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_connection_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with connection error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock connection error
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

    # Call function
    result = artifactory_list_items("test-repo", "/connection-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_timeout_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with timeout error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock timeout error
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    # Call function
    result = artifactory_list_items("test-repo", "/timeout-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_connection_error(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with connection error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock connection error
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

    # Call function
    result = artifactory_get_item_info("test-repo", "/connection-error")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())


class TestArtifactoryEdgeCases(unittest.TestCase):
  """Tests for edge cases in Artifactory API functions."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_empty_response(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with empty response from API."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock empty response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/empty")

    # Assertions
    self.assertEqual(result, {"uri": "", "created": "", "size": 0})

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_malformed_json(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with malformed JSON response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock malformed JSON response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/malformed")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_network_timeout(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with network timeout."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock network timeout
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    # Call function
    result = artifactory_list_items("test-repo", "/timeout")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_empty_query(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with empty query string."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with empty query
    result = artifactory_search_items("", ["repo1"])

    # Assertions
    self.assertEqual(result, [])
    mock_post.assert_called_once()
    # Verify AQL query contains empty search pattern
    self.assertIn("**", mock_post.call_args[1]["data"])

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_malformed_json(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with malformed JSON response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock malformed JSON response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_post.return_value = mock_response

    # Call function
    result = artifactory_search_items("test-query", ["repo1"])

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_network_timeout(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with network timeout."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock network timeout
    mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

    # Call function
    result = artifactory_search_items("test-query", ["repo1"])

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_empty_response(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with empty response from API."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock empty response for both main request and properties request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "test/path")

    # Assertions - empty response for a file would have properties added
    self.assertEqual(result, {"properties": {}})

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_malformed_json(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with malformed JSON response."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock malformed JSON response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/malformed")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_network_timeout(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with network timeout."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock network timeout
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    # Call function
    result = artifactory_get_item_info("test-repo", "/timeout")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch.dict(os.environ, {}, clear=True)
  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_list_items_invalid_parameters(self, mock_validate):
    """Test list_items with invalid parameters."""
    mock_validate.return_value = True

    # Test with None repository
    result = artifactory_list_items(None, "/path")
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with empty repository
    result = artifactory_list_items("", "/path")
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with None path
    result = artifactory_list_items("repo", None)
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch.dict(os.environ, {}, clear=True)
  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_search_items_invalid_parameters(self, mock_validate):
    """Test search_items with invalid parameters."""
    mock_validate.return_value = True

    # Test with None query
    result = artifactory_search_items(None, ["repo1"])
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with None repositories
    result = artifactory_search_items("query", None)
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with empty repositories list
    result = artifactory_search_items("query", [])
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch.dict(os.environ, {}, clear=True)
  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  def test_get_item_info_invalid_parameters(self, mock_validate):
    """Test get_item_info with invalid parameters."""
    mock_validate.return_value = True

    # Test with None repository
    result = artifactory_get_item_info(None, "/path")
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with empty repository
    result = artifactory_get_item_info("", "/path")
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

    # Test with None path
    result = artifactory_get_item_info("repo", None)
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_connection_error(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with connection error."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock connection error
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

    # Call function
    result = artifactory_search_items("test-query")

    # Assertions
    self.assertIn("error", result)
    self.assertIn("unexpected error", result["error"].lower())

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_invalid_path_characters(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with invalid path characters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "size": 100}
    mock_get.return_value = mock_response

    # Call function with path containing special characters
    result = artifactory_get_item_info("test-repo", "/path with spaces/file@name.txt")

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    # Verify URL encoding is handled properly
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path with spaces/file@name.txt", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_properties_request_fails(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info when properties request fails but main request succeeds."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock responses - first succeeds, second fails
    file_response = MagicMock()
    file_response.status_code = 200
    file_response.json.return_value = {"uri": "/test-file", "size": 1024}

    props_response = MagicMock()
    props_response.status_code = 403
    props_response.text = "Forbidden"

    mock_get.side_effect = [file_response, props_response]

    # Call function
    result = artifactory_get_item_info("test-repo", "/test-file")

    # Assertions - should return file info without properties
    self.assertEqual(result, {"uri": "/test-file", "size": 1024})
    self.assertEqual(mock_get.call_count, 2)


class TestArtifactoryAQLQueryConstruction(unittest.TestCase):
  """Tests for AQL query construction in Artifactory search function."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_single_repository(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with single repository in AQL query."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "results": [{"name": "test.jar", "repo": "test-repo"}]
    }
    mock_post.return_value = mock_response

    # Call function with single repository
    result = artifactory_search_items("*.jar", ["test-repo"])

    # Assertions
    self.assertIsInstance(result, list)
    mock_post.assert_called()
    # Verify AQL query construction
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn('"test-repo"', posted_data)
    self.assertIn("*.jar", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_multiple_repositories(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with multiple repositories in AQL query."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "results": [{"name": "test.jar", "repo": "repo1"}]
    }
    mock_post.return_value = mock_response

    # Call function with multiple repositories
    result = artifactory_search_items("*.jar", ["repo1", "repo2", "repo3"])

    # Assertions
    self.assertIsInstance(result, list)
    mock_post.assert_called()
    # Verify AQL query includes all repositories
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn('"repo1"', posted_data)
    self.assertIn('"repo2"', posted_data)
    self.assertIn('"repo3"', posted_data)
    self.assertIn("*.jar", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_complex_pattern(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with complex search pattern."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with complex pattern
    complex_pattern = "com/example/**/version-*.jar"
    result = artifactory_search_items(complex_pattern, ["maven-repo"])

    # Assertions
    self.assertIsInstance(result, list)
    mock_post.assert_called()
    # Verify complex pattern is included in AQL
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn(complex_pattern, posted_data)
    self.assertIn('"maven-repo"', posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_special_characters_in_pattern(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with special characters in search pattern."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with special characters
    special_pattern = "test-file_v1.2.3-SNAPSHOT.jar"
    result = artifactory_search_items(special_pattern, ["test-repo"])

    # Assertions
    self.assertIsInstance(result, list)
    mock_post.assert_called()
    # Verify special characters are handled properly
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn(special_pattern, posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_empty_repository_list(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with empty repository list."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with empty repository list
    result = artifactory_search_items("*.jar", [])

    # Assertions
    self.assertIsInstance(result, list)
    mock_post.assert_called()
    # Verify AQL query handles empty repository list
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn("*.jar", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_wildcard_patterns(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with various wildcard patterns."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Test different wildcard patterns
    patterns = ["*", "**/*", "*.jar", "test-*-*.jar", "**/target/*.jar"]

    for pattern in patterns:
      with self.subTest(pattern=pattern):
        result = artifactory_search_items(pattern, ["test-repo"])

        # Assertions
        self.assertIsInstance(result, list)
        mock_post.assert_called()
        # Verify pattern is included in AQL
        posted_data = mock_post.call_args[1]["data"]
        self.assertIn(pattern, posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_aql_query_structure_single_repo(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test AQL query structure for single repository search."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function
    artifactory_search_items("test.jar", ["maven-repo"])

    # Verify AQL query structure
    posted_data = mock_post.call_args[1]["data"]

    # Should contain proper AQL structure with $and, $or operators
    self.assertIn("items.find", posted_data)
    self.assertIn('"$and"', posted_data)
    self.assertIn('"$or"', posted_data)
    self.assertIn('"name"', posted_data)
    self.assertIn('"path"', posted_data)
    self.assertIn('"$match"', posted_data)
    self.assertIn('"repo"', posted_data)
    self.assertIn('"maven-repo"', posted_data)
    self.assertIn("*test.jar*", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_aql_query_structure_multiple_repos(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test AQL query structure for multiple repository search."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with multiple repositories
    artifactory_search_items("*.war", ["repo1", "repo2", "repo3"])

    # Verify AQL query structure
    posted_data = mock_post.call_args[1]["data"]

    # Should contain all repositories in OR condition
    self.assertIn('"repo":"repo1"', posted_data)
    self.assertIn('"repo":"repo2"', posted_data)
    self.assertIn('"repo":"repo3"', posted_data)
    # Should have proper nested structure
    self.assertIn('"$and"', posted_data)
    self.assertIn("**.war*", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_aql_query_no_repositories(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test AQL query structure when no repositories specified."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with empty repository list
    artifactory_search_items("test.jar", [])

    # Verify AQL query structure without repository filter
    posted_data = mock_post.call_args[1]["data"]

    # Should not contain $and operator when no repo filter
    self.assertNotIn('"$and"', posted_data)
    # Should still contain name and path matching
    self.assertIn('"$or"', posted_data)
    self.assertIn('"name"', posted_data)
    self.assertIn('"path"', posted_data)
    self.assertIn("*test.jar*", posted_data)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_query_with_quotes_and_escaping(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with queries containing quotes and special characters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Test queries with special characters
    special_queries = [
      'file"with"quotes.jar',
      "file'with'apostrophes.jar",
      "file[with]brackets.jar",
      "file{with}braces.jar",
      "file\\with\\backslashes.jar",
    ]

    for query in special_queries:
      with self.subTest(query=query):
        result = artifactory_search_items(query, ["test-repo"])

        # Verify the query is included in AQL
        posted_data = mock_post.call_args[1]["data"]
        self.assertIn(query, posted_data)
        self.assertIsInstance(result, list)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_repository_names_with_special_characters(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with repository names containing special characters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Test repositories with special characters
    special_repos = [
      "repo-with-dashes",
      "repo_with_underscores",
      "repo.with.dots",
      "repo123with456numbers",
      "REPO-WITH-CAPS",
    ]

    result = artifactory_search_items("*.jar", special_repos)

    # Verify all repository names are included in AQL
    posted_data = mock_post.call_args[1]["data"]
    for repo in special_repos:
      self.assertIn(f'"{repo}"', posted_data)
    self.assertIsInstance(result, list)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_very_long_query_pattern(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with very long query patterns."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Create a very long query pattern
    long_pattern = (
      "com/example/very/long/path/with/many/segments/" + "a" * 100 + "/*.jar"
    )

    result = artifactory_search_items(long_pattern, ["maven-repo"])

    # Verify the long pattern is handled correctly
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn(long_pattern, posted_data)
    self.assertIsInstance(result, list)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_unicode_patterns_and_repos(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items with Unicode characters in patterns and repository names."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Test with Unicode characters
    unicode_pattern = "测试文件-*.jar"
    unicode_repos = ["测试仓库", "репозиторий", "リポジトリ"]

    result = artifactory_search_items(unicode_pattern, unicode_repos)

    # Verify Unicode characters are handled correctly
    posted_data = mock_post.call_args[1]["data"]
    self.assertIn(unicode_pattern, posted_data)
    for repo in unicode_repos:
      self.assertIn(repo, posted_data)
    self.assertIsInstance(result, list)


class TestArtifactoryPathNormalization(unittest.TestCase):
  """Tests for path normalization in Artifactory API functions."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_path_with_leading_slash(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with path that has leading slash."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response for directory
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "uri": "/test",
      "children": [{"uri": "/item1"}, {"uri": "/item2"}],
    }
    mock_get.return_value = mock_response

    # Call function with leading slash
    result = artifactory_list_items("test-repo", "/path/to/item")

    # Assertions
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 2)
    mock_get.assert_called()
    # Verify URL construction handles leading slash properly
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path/to/item", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_path_without_leading_slash(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with path that doesn't have leading slash."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response for directory
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "children": [{"uri": "/item1"}]}
    mock_get.return_value = mock_response

    # Call function without leading slash
    result = artifactory_list_items("test-repo", "path/to/item")

    # Assertions
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 1)
    mock_get.assert_called()
    # Verify URL construction handles missing leading slash
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path/to/item", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_root_path(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with root path."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response for root directory
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "uri": "/",
      "children": [{"uri": "/folder1"}, {"uri": "/folder2"}],
    }
    mock_get.return_value = mock_response

    # Call function with root path
    result = artifactory_list_items("test-repo", "/")

    # Assertions
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 2)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    self.assertIn("test-repo/", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_path_with_double_slashes(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with path containing double slashes."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "size": 100}
    mock_get.return_value = mock_response

    # Call function with double slashes in path
    result = artifactory_get_item_info("test-repo", "/path//to//item")

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    # Verify double slashes are handled properly
    self.assertIn("/path//to//item", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_path_with_trailing_slash(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with path that has trailing slash."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test/", "size": 0}
    mock_get.return_value = mock_response

    # Call function with trailing slash
    result = artifactory_get_item_info("test-repo", "/path/to/directory/")

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path/to/directory/", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_empty_path(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with empty path."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/", "children": []}
    mock_get.return_value = mock_response

    # Call function with empty path
    result = artifactory_get_item_info("test-repo", "")

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    # Verify empty path is handled properly
    self.assertIn("test-repo", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_path_with_spaces(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items with path containing spaces."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "children": [{"uri": "/item1"}]}
    mock_get.return_value = mock_response

    # Call function with spaces in path
    result = artifactory_list_items("test-repo", "/path with spaces/to item")

    # Assertions
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 1)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path with spaces/to item", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_path_with_special_characters(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with path containing special characters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "size": 100}
    mock_get.return_value = mock_response

    # Call function with special characters in path
    result = artifactory_get_item_info(
      "test-repo", "/path/with-special_chars@#$%/file.txt"
    )

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path/with-special_chars@#$%/file.txt", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_path_normalization_trailing_slash_removal(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items removes trailing slash from non-root paths."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "children": [{"uri": "/item1"}]}
    mock_get.return_value = mock_response

    # Call function with trailing slash on non-root path
    result = artifactory_list_items("test-repo", "/path/to/directory/")

    # Assertions
    self.assertIsInstance(result, list)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    # Verify trailing slash is removed for non-root paths
    self.assertIn("/path/to/directory", called_url)
    self.assertNotIn("/path/to/directory/", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_root_path_preserves_trailing_slash(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items preserves trailing slash for root path."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/", "children": [{"uri": "/folder1"}]}
    mock_get.return_value = mock_response

    # Call function with root path
    result = artifactory_list_items("test-repo", "/")

    # Assertions
    self.assertIsInstance(result, list)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    # Verify root path is preserved
    self.assertIn("test-repo/", called_url)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_get_item_info_path_with_unicode_characters(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info with path containing Unicode characters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test", "size": 100}
    mock_get.return_value = mock_response

    # Call function with Unicode characters in path
    result = artifactory_get_item_info(
      "test-repo", "/path/with/ünïcödé/characters/文件.txt"
    )

    # Assertions
    self.assertIn("uri", result)
    mock_get.assert_called()
    called_url = mock_get.call_args[0][0]
    self.assertIn("/path/with/ünïcödé/characters/文件.txt", called_url)


class TestArtifactoryCachingBehavior(unittest.TestCase):
  """Tests for caching behavior in Artifactory API functions."""

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_list_items_cache_miss_and_set(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items cache miss scenario and cache setting."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None  # Cache miss
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    response_data = {"uri": "/test", "children": [{"uri": "/item1"}]}
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_list_items("test-repo", "/path")

    # Assertions
    self.assertEqual(result, response_data["children"])
    mock_cache_get.assert_called_once()
    mock_cache_set.assert_called_once()
    # Verify cache key format
    cache_key = mock_cache_get.call_args[0][0]
    self.assertIn("list_items", cache_key)
    self.assertIn("test-repo", cache_key)
    self.assertIn("/path", cache_key)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_list_items_cache_hit(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test list_items cache hit scenario."""
    # Setup mocks
    mock_validate.return_value = True
    cached_data = {"uri": "/cached", "children": []}
    mock_cache_get.return_value = cached_data  # Cache hit
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Call function
    result = artifactory_list_items("test-repo", "/path")

    # Assertions
    self.assertEqual(result, cached_data)
    mock_cache_get.assert_called_once()
    # Verify no HTTP request was made
    mock_get.assert_not_called()

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_search_items_cache_key_generation(
    self, mock_cache_set, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test search_items cache key generation with different parameters."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    response_data = {"results": []}
    mock_response.json.return_value = response_data
    mock_post.return_value = mock_response

    # Call function with multiple repositories
    result = artifactory_search_items("*.jar", ["repo1", "repo2"])

    # Assertions
    self.assertEqual(result, response_data["results"])
    mock_cache_get.assert_called_once()
    mock_cache_set.assert_called_once()
    # Verify cache key includes all repositories and pattern
    cache_key = mock_cache_get.call_args[0][0]
    self.assertIn("search_items", cache_key)
    self.assertIn("repo1", cache_key)
    self.assertIn("repo2", cache_key)
    self.assertIn("*.jar", cache_key)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_get_item_info_cache_ttl_setting(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test get_item_info cache TTL setting."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    response_data = {"uri": "/test", "size": 1024}
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    # Call function
    result = artifactory_get_item_info("test-repo", "/path/to/item")

    # Assertions
    self.assertEqual(result, response_data)
    mock_cache_set.assert_called_once()
    # Verify cache TTL is set (should be 300 seconds based on implementation)
    cache_set_args = mock_cache_set.call_args
    self.assertEqual(len(cache_set_args[0]), 2)  # key, value
    self.assertIn("ttl", cache_set_args[1])  # ttl as keyword argument
    ttl = cache_set_args[1]["ttl"]
    self.assertEqual(ttl, 300)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_cache_key_uniqueness(
    self, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test that different parameters generate unique cache keys."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"uri": "/test"}
    mock_get.return_value = mock_response

    # Call function with different parameters
    artifactory_list_items("repo1", "/path1")
    cache_key1 = mock_cache_get.call_args[0][0]

    artifactory_list_items("repo2", "/path1")
    cache_key2 = mock_cache_get.call_args[0][0]

    artifactory_list_items("repo1", "/path2")
    cache_key3 = mock_cache_get.call_args[0][0]

    # Assertions - all cache keys should be different
    self.assertNotEqual(cache_key1, cache_key2)
    self.assertNotEqual(cache_key1, cache_key3)
    self.assertNotEqual(cache_key2, cache_key3)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.post")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  def test_search_items_cache_with_sorted_repositories(
    self, mock_cache_get, mock_post, mock_auth, mock_validate
  ):
    """Test that repository order doesn't affect cache key generation."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = {"Authorization": "Bearer test-token"}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    # Call function with repositories in different order
    artifactory_search_items("*.jar", ["repo1", "repo2", "repo3"])
    cache_key1 = mock_cache_get.call_args[0][0]

    artifactory_search_items("*.jar", ["repo3", "repo1", "repo2"])
    cache_key2 = mock_cache_get.call_args[0][0]

    # Assertions - cache keys should be the same (repositories should be sorted)
    self.assertEqual(cache_key1, cache_key2)

  @patch("devops_mcps.utils.artifactory.artifactory_api.validate_artifactory_config")
  @patch("devops_mcps.utils.artifactory.artifactory_api.get_auth")
  @patch("requests.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.get")
  @patch("devops_mcps.utils.artifactory.artifactory_api.cache.set")
  def test_cache_behavior_with_special_characters(
    self, mock_cache_set, mock_cache_get, mock_get, mock_auth, mock_validate
  ):
    """Test cache behavior with special characters in paths."""
    # Setup mocks
    mock_validate.return_value = True
    mock_cache_get.return_value = None
    mock_auth.return_value = ("user", "pass")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    response_data = {"uri": "/test", "size": 100}
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    # Call function with special characters in path
    special_path = "/path/with spaces/and-dashes/file_name.jar"
    result = artifactory_get_item_info("test-repo", special_path)

    # Assertions
    self.assertEqual(result, response_data)
    mock_cache_get.assert_called_once()
    mock_cache_set.assert_called_once()
    # Verify cache key handles special characters
    cache_key = mock_cache_get.call_args[0][0]
    self.assertIsInstance(cache_key, str)
    self.assertIn("get_item_info", cache_key)


if __name__ == "__main__":
  unittest.main()
