import os
import unittest
from unittest.mock import patch, MagicMock

from devops_mcps.artifactory import (
  _get_auth,
  _validate_artifactory_config,
  artifactory_list_items,
  artifactory_search_items,
  artifactory_get_item_info,
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
  @patch("devops_mcps.artifactory.cache.set")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
  @patch("devops_mcps.artifactory.cache.set")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory.cache.get")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.post")
  @patch("devops_mcps.artifactory.cache.get")
  @patch("devops_mcps.artifactory.cache.set")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.post")
  @patch("devops_mcps.artifactory.cache.get")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory.cache.get")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
  @patch("devops_mcps.artifactory.cache.set")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
  @patch("devops_mcps.artifactory.cache.set")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory._get_auth")
  @patch("requests.get")
  @patch("devops_mcps.artifactory.cache.get")
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

  @patch("devops_mcps.artifactory._validate_artifactory_config")
  @patch("devops_mcps.artifactory.cache.get")
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


if __name__ == "__main__":
  unittest.main()
