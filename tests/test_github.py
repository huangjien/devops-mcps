import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock, call

from devops_mcps.github import (
  initialize_github_client,
  gh_search_repositories,
  gh_get_file_contents,
  gh_list_commits,
  gh_list_issues,
  gh_get_repository,
  gh_search_code,
  gh_get_issue_content,
  gh_get_current_user_info,
  # Legacy wrapper functions
  search_repositories,
  get_current_user_info,
  get_file_contents,
  list_commits,
  list_issues,
  get_repository,
  search_code,
  get_issue_details,
  get_github_issue_content,
)
from devops_mcps.utils.github.github_converters import _to_dict, _handle_paginated_list
from github import (
  UnknownObjectException,
  BadCredentialsException,
  RateLimitExceededException,
  GithubException,
)
from github.Repository import Repository
from github.Commit import Commit
from github.Issue import Issue
from github.ContentFile import ContentFile
from github.PaginatedList import PaginatedList

# --- Test Fixtures ---


@pytest.fixture
def mock_env_vars(monkeypatch):
  """Set up mock environment variables for GitHub client."""
  monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
  yield


@pytest.fixture
def mock_github():
  with patch("devops_mcps.utils.github_client.Github") as mock:
    yield mock


@pytest.fixture
def mock_github_api(mock_env_vars):
  """Mock GitHub API and initialize client."""
  with patch("devops_mcps.utils.github_client.Github", autospec=True) as mock_github:
    mock_instance = mock_github.return_value
    mock_instance.get_user.return_value = MagicMock(login="test_user")
    mock_instance.get_rate_limit.return_value = MagicMock()
    mock_instance.get_repo.return_value = MagicMock()

    # Add all the methods that tests are trying to mock
    mock_instance.search_code = MagicMock()
    mock_instance.search_repositories = MagicMock()
    mock_instance.search_issues = MagicMock()
    mock_instance.search_users = MagicMock()

    # Patch the global client directly
    with patch("devops_mcps.utils.github_client.g", new=mock_instance):
      yield mock_instance


def test_gh_list_commits_network_error(mock_github_api, mock_env_vars):
  """Test commit listing when network error occurs."""
  mock_github_api.get_repo.side_effect = GithubException(
    500, {"message": "Network Error"}, {}
  )

  result = gh_list_commits("owner", "repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert "500" in result["error"]
  assert "network error" in result["error"].lower()


def test_gh_search_repositories_invalid_query(mock_github_api, mock_env_vars):
  """Test repository search with invalid query."""
  mock_github_api.search_repositories.side_effect = GithubException(
    422, {"message": "Invalid query"}, {}
  )

  result = gh_search_repositories(query="invalid:query")
  assert isinstance(result, dict)
  assert "error" in result
  assert "422" in result["error"]
  assert "invalid query" in result["error"].lower()


def test_gh_get_file_contents_file_not_found(mock_github_api, mock_env_vars):
  """Test file content retrieval when file doesn't exist."""
  mock_repo = MagicMock()
  mock_repo.get_contents.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}, {}
  )
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_file_contents("owner", "repo", "path/to/file")
  assert isinstance(result, dict)
  assert "error" in result
  assert "not found" in result["error"].lower()


def test_gh_get_repository_unauthorized(mock_github_api, mock_env_vars):
  """Test repository access when unauthorized."""
  mock_github_api.get_repo.side_effect = GithubException(
    401, {"message": "Unauthorized access"}, {}
  )

  result = gh_get_repository("owner", "private-repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert "401" in result["error"]
  assert "unauthorized" in result["error"].lower()


def test_gh_list_issues_forbidden(mock_github_api, mock_env_vars):
  """Test issue listing when access is forbidden."""
  mock_repo = MagicMock()
  mock_repo.get_issues.side_effect = GithubException(403, {"message": "Forbidden"}, {})
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_issues("owner", "repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert "403" in result["error"]
  assert "forbidden" in result["error"].lower()


def test_initialize_github_client_network_error(monkeypatch, mock_github_api):
  """Test initialization failure due to network error."""
  monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
  mock_github_api.get_user.side_effect = GithubException(503, "Service Unavailable")

  client = initialize_github_client(force=True)
  assert client is None


@pytest.fixture
def mock_cache():
  # Create a generic cache mock that can be used across different modules
  mock = Mock()
  mock.get.return_value = None
  mock.set.return_value = None
  yield mock


@pytest.fixture
def mock_logger():
  with patch("devops_mcps.utils.github_client.logger") as mock:
    yield mock


@pytest.fixture
def mock_api_logger():
  """Generic logger mock - deprecated, use specific module logger patches instead"""
  mock = Mock()
  yield mock


@pytest.fixture
def mock_converters_logger():
  with patch("devops_mcps.utils.github_converters.logger") as mock:
    yield mock


# --- Test initialize_github_client ---


def test_initialize_github_client_with_token(mock_github, mock_logger):
  # Setup
  mock_instance = mock_github.return_value
  mock_instance.get_user.return_value.login = "test_user"

  # Execute
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
    with patch("devops_mcps.utils.github.github_client.g", None):  # Reset global client
      client = initialize_github_client(force=True)

  # Verify
  assert client is not None
  mock_github.assert_called_once()
  # Check that the call was made with the expected parameters
  call_args = mock_github.call_args
  assert call_args is not None
  assert call_args[1]["timeout"] == 60
  assert call_args[1]["per_page"] == 10
  assert call_args[1]["base_url"] == "https://api.github.com"
  assert "auth" in call_args[1]
  mock_logger.info.assert_called_once()


def test_initialize_github_client_without_token(mock_github, mock_logger):
  # Setup
  mock_instance = mock_github.return_value
  mock_instance.get_rate_limit.return_value = True

  # Execute
  with patch.dict("os.environ", {}, clear=True):
    with patch("devops_mcps.utils.github_client.g", None):  # Reset global client
      client = initialize_github_client(force=True)

  # Verify
  assert client is None
  mock_github.assert_not_called()
  mock_logger.error.assert_called_once()


def test_initialize_github_client_bad_credentials(mock_github, mock_logger):
  # Setup
  mock_instance = mock_github.return_value
  mock_instance.get_user.side_effect = BadCredentialsException(
    401, {"message": "Bad credentials"}
  )

  # Execute
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "invalid_token"}):
    with patch("devops_mcps.utils.github_client.g", None):  # Reset global client
      client = initialize_github_client(force=True)

  # Verify
  assert client is None
  mock_logger.error.assert_called_once_with(
    "GitHub authentication test failed: 401 - {'message': 'Bad credentials'}"
  )


def test_initialize_github_client_rate_limit_exceeded(mock_github, mock_logger):
  """Test GitHub client initialization with rate limit exceeded."""
  mock_github.return_value.get_user.side_effect = RateLimitExceededException(
    403, {"message": "API rate limit exceeded"}
  )

  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "valid_token"}):
    with patch("devops_mcps.utils.github_client.g", None):  # Reset global client
      result = initialize_github_client(force=True)
      assert result is None
      mock_logger.error.assert_called_with(
        "GitHub authentication test failed: 403 - {'message': 'API rate limit exceeded'}"
      )


def test_initialize_github_client_unauthenticated_error(mock_github, mock_logger):
  """Test GitHub client initialization when no token is provided."""

  with patch.dict(os.environ, {}, clear=True):  # No token
    result = initialize_github_client(force=True)
    assert result is None
    mock_github.assert_not_called()
    mock_logger.error.assert_called_once()


def test_initialize_github_client_with_custom_api_url(mock_github, mock_logger):
  """Test GitHub client initialization with custom API URL."""
  mock_user = Mock()
  mock_user.login = "test_user"
  mock_github.return_value.get_user.return_value = mock_user

  with patch.dict(
    os.environ,
    {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "valid_token",
      "GITHUB_API_URL": "https://github.enterprise.com/api/v3",
    },
  ):
    result = initialize_github_client(force=True)
    assert result is not None
    mock_github.assert_called_with(
      auth=mock_github.call_args[1]["auth"],
      timeout=60,
      per_page=10,
      base_url="https://github.enterprise.com/api/v3",
    )


# Removed test_initialize_github_client_already_initialized as the current implementation
# always resets g = None, making this scenario untestable


# --- Test _to_dict ---


def test_to_dict_with_repository():
  mock_repo = Mock(spec=Repository)
  mock_repo.full_name = "owner/repo"
  mock_repo.name = "repo"
  mock_repo.description = "Test repo"
  mock_repo.html_url = "https://github.com/owner/repo"
  mock_repo.language = "Python"
  mock_repo.private = False
  mock_repo.default_branch = "main"
  mock_repo.owner.login = "owner"

  result = _to_dict(mock_repo)

  assert isinstance(result, dict)
  assert result["full_name"] == "owner/repo"
  assert result["name"] == "repo"
  assert result["language"] == "Python"


def test_to_dict_with_commit():
  mock_commit = Mock(spec=Commit)
  mock_commit.sha = "abc123"
  mock_commit.html_url = "https://github.com/owner/repo/commit/abc123"
  mock_commit.commit = Mock()
  mock_commit.commit.message = "Test commit"
  mock_commit.commit.author = Mock()
  mock_commit.commit.author.name = "test author"
  mock_commit.commit.author.date = "2023-01-01"
  mock_commit.commit.author._rawData = {"name": "test author", "date": "2023-01-01"}

  result = _to_dict(mock_commit)

  assert isinstance(result, dict)
  assert result["sha"] == "abc123"
  assert result["message"] == "Test commit"
  assert isinstance(result["author"], dict)
  assert result["author"]["name"] == "test author"


def test_to_dict_with_issue():
  """Test _to_dict with Issue object."""
  mock_issue = Mock(spec=Issue)
  mock_issue.number = 123
  mock_issue.title = "Test Issue"
  mock_issue.state = "open"
  mock_issue.html_url = "https://github.com/owner/repo/issues/123"
  mock_issue.user = Mock()
  mock_issue.user.login = "testuser"
  mock_issue.labels = [Mock(name="bug"), Mock(name="enhancement")]
  mock_issue.labels[0].name = "bug"
  mock_issue.labels[1].name = "enhancement"
  mock_issue.assignees = [Mock(login="assignee1"), Mock(login="assignee2")]
  mock_issue.assignees[0].login = "assignee1"
  mock_issue.assignees[1].login = "assignee2"
  mock_issue.assignee = None
  mock_issue.pull_request = None

  result = _to_dict(mock_issue)
  assert result["number"] == 123
  assert result["title"] == "Test Issue"
  assert result["state"] == "open"
  assert result["html_url"] == "https://github.com/owner/repo/issues/123"
  assert result["user_login"] == "testuser"
  assert result["label_names"] == ["bug", "enhancement"]
  assert result["assignee_logins"] == ["assignee1", "assignee2"]
  assert result["is_pull_request"] is False


def test_to_dict_with_git_author():
  """Test _to_dict with GitAuthor object."""
  from github.GitAuthor import GitAuthor

  mock_author = Mock(spec=GitAuthor)
  mock_author.name = "Test Author"
  mock_author.date = "2023-01-01T00:00:00Z"

  result = _to_dict(mock_author)
  assert result["name"] == "Test Author"
  assert result["date"] == "2023-01-01T00:00:00Z"


def test_to_dict_with_label():
  """Test _to_dict with Label object."""
  from github.Label import Label

  mock_label = Mock(spec=Label)
  mock_label.name = "bug"

  result = _to_dict(mock_label)
  assert result["name"] == "bug"


def test_to_dict_with_license():
  """Test _to_dict with License object."""
  from github.License import License

  mock_license = Mock(spec=License)
  mock_license.name = "MIT License"
  mock_license.spdx_id = "MIT"

  result = _to_dict(mock_license)
  assert result["name"] == "MIT License"
  assert result["spdx_id"] == "MIT"


def test_to_dict_with_milestone():
  """Test _to_dict with Milestone object."""
  from github.Milestone import Milestone

  mock_milestone = Mock(spec=Milestone)
  mock_milestone.title = "v1.0"
  mock_milestone.state = "open"

  result = _to_dict(mock_milestone)
  assert result["title"] == "v1.0"
  assert result["state"] == "open"


def test_to_dict_with_content_file():
  """Test _to_dict with ContentFile object."""
  from github.ContentFile import ContentFile

  mock_content = Mock(spec=ContentFile)
  mock_content.name = "test.py"
  mock_content.path = "src/test.py"
  mock_content.html_url = "https://github.com/owner/repo/blob/main/src/test.py"
  mock_content.type = "file"
  mock_content.size = 1024
  mock_content.repository = Mock()
  mock_content.repository.full_name = "owner/repo"

  result = _to_dict(mock_content)
  assert result["name"] == "test.py"
  assert result["path"] == "src/test.py"
  assert result["html_url"] == "https://github.com/owner/repo/blob/main/src/test.py"
  assert result["type"] == "file"
  assert result["size"] == 1024
  assert result["repository_full_name"] == "owner/repo"


def test_to_dict_with_basic_types():
  """Test _to_dict with basic Python types."""
  assert _to_dict("string") == "string"
  assert _to_dict(123) == 123
  assert _to_dict(45.67) == 45.67
  assert _to_dict(True) is True
  assert _to_dict(None) is None


def test_to_dict_with_list():
  """Test _to_dict with list containing various types."""
  test_list = ["string", 123, True, None]
  result = _to_dict(test_list)
  assert result == ["string", 123, True, None]


def test_to_dict_with_dict():
  """Test _to_dict with dictionary."""
  test_dict = {"key1": "value1", "key2": 123, "key3": None}
  result = _to_dict(test_dict)
  assert result == {"key1": "value1", "key2": 123, "key3": None}


def test_to_dict_with_unknown_object():
  """Test _to_dict with unknown object type."""

  class UnknownObject:
    def __init__(self):
      self.attr = "value"

  unknown_obj = UnknownObject()
  result = _to_dict(unknown_obj)
  # Should return string representation for unknown types
  assert result == "<Object of type UnknownObject>"


def test_to_dict_with_named_user():
  """Test _to_dict with NamedUser object."""
  from github.NamedUser import NamedUser

  mock_user = Mock(spec=NamedUser)
  mock_user.login = "testuser"
  mock_user.html_url = "https://github.com/testuser"
  mock_user.type = "User"

  result = _to_dict(mock_user)
  assert result["login"] == "testuser"
  assert result["html_url"] == "https://github.com/testuser"
  assert result["type"] == "User"


def test_to_dict_with_nested_objects():
  """Test _to_dict with nested GitHub objects."""
  mock_repo = Mock(spec=Repository)
  mock_repo.full_name = "owner/repo"
  mock_repo.name = "repo"
  mock_repo.description = "Test repo"
  mock_repo.html_url = "https://github.com/owner/repo"
  mock_repo.language = "Python"
  mock_repo.private = False
  mock_repo.default_branch = "main"
  mock_repo.owner = Mock()
  mock_repo.owner.login = "owner"

  # Test with list containing the repository
  test_list = [mock_repo, "string", 123]
  result = _to_dict(test_list)

  assert len(result) == 3
  assert isinstance(result[0], dict)
  assert result[0]["full_name"] == "owner/repo"
  assert result[1] == "string"
  assert result[2] == 123


def test_to_dict_with_nested_dict():
  """Test _to_dict with dictionary containing GitHub objects."""
  from github.Label import Label

  mock_label = Mock(spec=Label)
  mock_label.name = "bug"

  test_dict = {"label": mock_label, "count": 5, "metadata": {"nested": "value"}}

  result = _to_dict(test_dict)

  assert isinstance(result["label"], dict)
  assert result["label"]["name"] == "bug"
  assert result["count"] == 5
  assert result["metadata"]["nested"] == "value"


def test_to_dict_with_raw_data_fallback():
  """Test _to_dict with object that has _rawData attribute."""

  class ObjectWithRawData:
    def __init__(self):
      self._rawData = {"key1": "value1", "key2": 123}

  obj = ObjectWithRawData()
  result = _to_dict(obj)

  assert result == {"key1": "value1", "key2": 123}


def test_to_dict_with_mock_raw_data():
  """Test _to_dict with mock object containing mock values in _rawData."""

  mock_obj = Mock()
  mock_value = Mock()
  mock_value.return_value = "actual_value"
  mock_obj._rawData = {"key": mock_value, "simple": "value"}

  result = _to_dict(mock_obj)

  assert result["key"] == "actual_value"
  assert result["simple"] == "value"


def test_to_dict_with_mock_object_attributes():
  """Test _to_dict with mock object that has common attributes."""
  import unittest.mock

  mock_obj = unittest.mock.Mock()
  mock_obj.name = "test_name"
  mock_obj.full_name = "test_full_name"
  mock_obj.description = "test_description"
  # Ensure _rawData doesn't exist or is not a dict to trigger mock attribute handling
  del mock_obj._rawData

  result = _to_dict(mock_obj)

  assert result["name"] == "test_name"
  assert result["full_name"] == "test_full_name"
  assert result["description"] == "test_description"


def test_to_dict_with_mock_return_values():
  """Test _to_dict with mock object that has return_value attributes."""
  import unittest.mock

  mock_obj = unittest.mock.Mock()
  name_mock = unittest.mock.Mock()
  name_mock.return_value = "returned_name"
  mock_obj.name = name_mock
  # Ensure _rawData doesn't exist or is not a dict to trigger mock attribute handling
  del mock_obj._rawData

  result = _to_dict(mock_obj)

  assert result["name"] == "returned_name"


def test_to_dict_with_content_file_no_repository():
  """Test _to_dict with ContentFile object that has no repository."""
  from github.ContentFile import ContentFile

  mock_content = Mock(spec=ContentFile)
  mock_content.name = "test.py"
  mock_content.path = "src/test.py"
  mock_content.html_url = "https://github.com/owner/repo/blob/main/src/test.py"
  mock_content.type = "file"
  mock_content.size = 1024
  mock_content.repository = None

  result = _to_dict(mock_content)

  assert result["name"] == "test.py"
  assert result["repository_full_name"] is None


def test_to_dict_with_issue_single_assignee():
  """Test _to_dict with Issue object that has single assignee (no assignees list)."""
  mock_issue = Mock(spec=Issue)
  mock_issue.number = 456
  mock_issue.title = "Single Assignee Issue"
  mock_issue.state = "closed"
  mock_issue.html_url = "https://github.com/owner/repo/issues/456"
  mock_issue.user = Mock()
  mock_issue.user.login = "testuser"
  mock_issue.labels = []
  mock_issue.assignees = None  # No assignees list
  mock_issue.assignee = Mock()
  mock_issue.assignee.login = "single_assignee"
  mock_issue.pull_request = None

  result = _to_dict(mock_issue)

  assert result["assignee_logins"] == ["single_assignee"]


def test_to_dict_with_issue_no_user():
  """Test _to_dict with Issue object that has no user."""
  mock_issue = Mock(spec=Issue)
  mock_issue.number = 789
  mock_issue.title = "No User Issue"
  mock_issue.state = "open"
  mock_issue.html_url = "https://github.com/owner/repo/issues/789"
  mock_issue.user = None
  mock_issue.labels = []
  mock_issue.assignees = []
  mock_issue.assignee = None
  mock_issue.pull_request = None

  result = _to_dict(mock_issue)

  assert result["user_login"] is None
  assert result["assignee_logins"] == []


def test_to_dict_with_git_author_no_date():
  """Test _to_dict with GitAuthor object that has no date."""
  from github.GitAuthor import GitAuthor

  mock_author = Mock(spec=GitAuthor)
  mock_author.name = "Test Author"
  mock_author.date = None

  result = _to_dict(mock_author)

  assert result["name"] == "Test Author"
  assert result["date"] is None


def test_to_dict_with_issue_as_pull_request():
  """Test _to_dict with Issue object that is actually a pull request."""
  mock_issue = Mock(spec=Issue)
  mock_issue.number = 101
  mock_issue.title = "Pull Request Issue"
  mock_issue.state = "open"
  mock_issue.html_url = "https://github.com/owner/repo/pull/101"
  mock_issue.user = Mock()
  mock_issue.user.login = "pruser"
  mock_issue.labels = []
  mock_issue.assignees = []
  mock_issue.assignee = None
  mock_issue.pull_request = Mock()  # Not None, so it's a PR

  result = _to_dict(mock_issue)

  assert result["is_pull_request"] is True


# --- Test _handle_paginated_list ---


def test_handle_paginated_list(mock_converters_logger):
  mock_item1 = Mock()
  mock_item2 = Mock()
  mock_paginated = Mock(spec=PaginatedList)
  mock_paginated.get_page.return_value = [mock_item1, mock_item2]

  with patch("devops_mcps.utils.github_converters._to_dict") as mock_to_dict:
    mock_to_dict.side_effect = lambda x: {"mock": str(x)}
    result = _handle_paginated_list(mock_paginated)

  assert isinstance(result, list)
  assert len(result) == 2
  mock_paginated.get_page.assert_called_once_with(0)
  mock_converters_logger.debug.assert_called()


def test_handle_paginated_list_error(mock_converters_logger):
  mock_paginated = Mock(spec=PaginatedList)
  mock_paginated.get_page.side_effect = Exception("Test error")

  result = _handle_paginated_list(mock_paginated)

  assert isinstance(result, list)
  assert "error" in result[0]
  mock_converters_logger.error.assert_called()


# --- Test gh_search_repositories ---


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_repositories_success(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_search = Mock(spec=PaginatedList)
  mock_search.totalCount = 2
  # Mock the get_page method to return a list of mock repositories
  mock_repo1 = Mock(spec=Repository)
  mock_repo1.name = "repo1"
  mock_repo1.description = "Test repo 1"
  mock_repo1.html_url = "https://github.com/test/repo1"
  mock_repo1.language = "Python"
  mock_repo1.private = False
  mock_repo1.default_branch = "main"
  mock_repo1.owner.login = "test"

  mock_repo2 = Mock(spec=Repository)
  mock_repo2.name = "repo2"
  mock_repo2.description = "Test repo 2"
  mock_repo2.html_url = "https://github.com/test/repo2"
  mock_repo2.language = "JavaScript"
  mock_repo2.private = True
  mock_repo2.default_branch = "master"
  mock_repo2.owner.login = "test"

  mock_search.get_page.return_value = [mock_repo1, mock_repo2]
  mock_github_api.search_repositories.return_value = mock_search

  result = gh_search_repositories("test query")

  assert isinstance(result, list)
  assert len(result) == 2
  assert result[0]["name"] == "repo1"
  assert result[1]["name"] == "repo2"
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_repositories_cached(mock_cache_patch):
  mock_cache_patch.get.return_value = [{"name": "cached_repo"}]

  result = gh_search_repositories("test query")

  assert isinstance(result, list)
  assert result[0]["name"] == "cached_repo"
  mock_cache_patch.get.assert_called_once()


@patch("devops_mcps.utils.github.github_search_api.logger")
def test_gh_search_repositories_error(mock_logger, mock_github):
  mock_instance = mock_github.return_value
  mock_instance.search_repositories.side_effect = GithubException(
    403, {"message": "Rate limit exceeded"}
  )

  result = gh_search_repositories("test query")

  assert isinstance(result, dict)
  assert "error" in result
  assert "error" in result
  mock_logger.error.assert_called()


# --- Test gh_get_file_contents ---


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_file(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_content = Mock(spec=ContentFile)
  mock_content.type = "file"
  mock_content.encoding = "base64"
  mock_content.content = "dGVzdCBjb250ZW50"  # "test content" in base64
  mock_content.decoded_content = b"test content"
  mock_content._rawData = {
    "type": "file",
    "encoding": "base64",
    "content": "dGVzdCBjb250ZW50",
    "path": "path/to/file",
  }
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = mock_content

  result = gh_get_file_contents("owner", "repo", "path/to/file")

  assert result == "test content"
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_directory(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_content1 = Mock(spec=ContentFile)
  mock_content1._rawData = {"name": "file1", "type": "file"}
  mock_content2 = Mock(spec=ContentFile)
  mock_content2._rawData = {"name": "file2", "type": "file"}
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = [mock_content1, mock_content2]

  result = gh_get_file_contents("owner", "repo", "path/to/dir")

  assert isinstance(result, list)
  assert len(result) == 2
  assert len(result) == 2
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_repository_api.logger")
@patch("devops_mcps.utils.github.github_repository_api.initialize_github_client")
def test_gh_get_file_contents_not_found(mock_init_client, mock_logger):
  mock_instance = Mock()
  mock_init_client.return_value = mock_instance
  mock_repo = Mock()
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_contents.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}
  )

  result = gh_get_file_contents("owner", "repo", "invalid/path")

  assert isinstance(result, dict)
  assert "error" in result
  mock_logger.warning.assert_called()


# --- Test gh_list_commits ---


@patch("devops_mcps.utils.github.github_commit_api.cache")
def test_gh_list_commits_success(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_commits = Mock(spec=PaginatedList)
  # Mock the get_page method to return a list of mock commits
  mock_commit1 = Mock(spec=Commit)
  mock_commit1.sha = "abc123"
  mock_commit1.commit.message = "First commit"
  mock_commit1.commit.author.name = "John Doe"
  mock_commit1.commit.author.email = "john@example.com"
  mock_commit1.commit.author.date = "2023-01-01T00:00:00Z"
  mock_commit1.html_url = "https://github.com/owner/repo/commit/abc123"

  mock_commit2 = Mock(spec=Commit)
  mock_commit2.sha = "def456"
  mock_commit2.commit.message = "Second commit"
  mock_commit2.commit.author.name = "Jane Doe"
  mock_commit2.commit.author.email = "jane@example.com"
  mock_commit2.commit.author.date = "2023-01-02T00:00:00Z"
  mock_commit2.html_url = "https://github.com/owner/repo/commit/def456"

  mock_commits.get_page.return_value = [mock_commit1, mock_commit2]
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_commits.return_value = mock_commits

  result = gh_list_commits("owner", "repo", "main")

  assert isinstance(result, list)
  assert len(result) == 2
  assert result[0]["sha"] == "abc123"
  assert result[1]["sha"] == "def456"
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_commit_api.initialize_github_client")
@patch("devops_mcps.utils.github.github_commit_api.logger")
def test_gh_list_commits_empty_repo(mock_logger, mock_init_client, mock_github):
  mock_instance = mock_github.return_value
  mock_init_client.return_value = mock_instance
  mock_repo = Mock()
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_commits.side_effect = GithubException(
    409, {"message": "Git Repository is empty"}
  )

  result = gh_list_commits("owner", "repo")

  assert isinstance(result, dict)
  assert "error" in result
  mock_logger.warning.assert_called()


# --- Test gh_list_issues ---


@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_list_issues_success(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_issues = Mock(spec=PaginatedList)
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_issues.return_value = mock_issues

  # Mock issues with proper attributes
  mock_issue1 = Mock(spec=Issue)
  mock_issue1.number = 1
  mock_issue1.title = "Test Issue 1"
  mock_issue1.body = "This is test issue 1"
  mock_issue1.state = "open"
  mock_issue1.html_url = "https://github.com/owner/repo/issues/1"
  mock_issue1.created_at = "2023-01-01T00:00:00Z"
  mock_issue1.updated_at = "2023-01-01T00:00:00Z"
  mock_issue1.labels = []
  mock_issue1.assignees = []
  mock_issue1.user = None

  mock_issue2 = Mock(spec=Issue)
  mock_issue2.number = 2
  mock_issue2.title = "Test Issue 2"
  mock_issue2.body = "This is test issue 2"
  mock_issue2.state = "closed"
  mock_issue2.html_url = "https://github.com/owner/repo/issues/2"
  mock_issue2.created_at = "2023-01-02T00:00:00Z"
  mock_issue2.updated_at = "2023-01-02T00:00:00Z"
  mock_issue2.labels = []
  mock_issue2.assignees = []
  mock_issue2.user = None

  mock_issues.get_page.return_value = [mock_issue1, mock_issue2]

  result = gh_list_issues("owner", "repo", "open", ["bug"], "created", "desc")

  assert isinstance(result, list)
  assert len(result) == 2
  assert result[0]["number"] == 1
  assert result[0]["title"] == "Test Issue 1"
  assert result[0]["state"] == "open"
  assert result[1]["number"] == 2
  assert result[1]["title"] == "Test Issue 2"
  assert result[1]["state"] == "closed"
  mock_cache_patch.set.assert_called_once()


# --- Test gh_get_repository ---


@patch("devops_mcps.utils.github.github_repository_api.initialize_github_client")
@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_repository_success(mock_cache_patch, mock_init_client, mock_github):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_instance = mock_github.return_value
  mock_init_client.return_value = mock_instance
  mock_repo = Mock(spec=Repository)
  mock_repo._rawData = {
    "name": "test-repo",
    "full_name": "owner/repo",
    "description": "Test repository",
  }
  mock_instance.get_repo.return_value = mock_repo

  result = gh_get_repository("owner", "repo")

  assert isinstance(result, dict)
  assert result["name"] == "test-repo"
  mock_cache_patch.set.assert_called_once()


# --- Test gh_search_code ---


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_success(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_instance = mock_github_api
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 2

  # Mock ContentFile items
  mock_code_item1 = Mock(spec=ContentFile)
  mock_code_item1.type = "file"
  mock_code_item1.name = "file1.py"
  mock_code_item1.path = "file1.py"
  mock_code_item1.size = 1024
  mock_code_item1.html_url = "https://github.com/test/repo1/blob/main/file1.py"
  mock_code_item1.repository = Mock()
  mock_code_item1.repository.full_name = "test/repo1"

  mock_code_item2 = Mock(spec=ContentFile)
  mock_code_item2.type = "file"
  mock_code_item2.name = "file2.py"
  mock_code_item2.path = "file2.py"
  mock_code_item2.size = 2048
  mock_code_item2.html_url = "https://github.com/test/repo2/blob/main/file2.py"
  mock_code_item2.repository = Mock()
  mock_code_item2.repository.full_name = "test/repo2"

  mock_code_results.get_page.return_value = [mock_code_item1, mock_code_item2]
  mock_instance.search_code.return_value = mock_code_results

  result = gh_search_code("test query")

  assert isinstance(result, list)
  assert len(result) == 2
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_success(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with (
    patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}),
    patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client,
  ):
    mock_user = Mock()
    mock_user.login = "testuser"
    mock_user.name = "Test User"
    mock_user.email = "testuser@example.com"
    mock_user.id = 12345
    mock_user.html_url = "https://github.com/testuser"
    mock_user.type = "User"
    mock_client = Mock()
    mock_client.get_user.return_value = mock_user
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert result["login"] == "testuser"
    assert result["name"] == "Test User"
    assert result["email"] == "testuser@example.com"
    assert result["id"] == 12345
    assert result["html_url"] == "https://github.com/testuser"
    assert result["type"] == "User"


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_invalid_credentials(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_user.side_effect = BadCredentialsException(
        401, {"message": "Bad credentials"}
      )
      mock_init_client.return_value = mock_client
      from devops_mcps.github import gh_get_current_user_info

      result = gh_get_current_user_info()
      assert "error" in result
      assert "Authentication failed" in result["error"]


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_unexpected_error(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_user.side_effect = Exception("Unexpected error")
      mock_init_client.return_value = mock_client
      from devops_mcps.github import gh_get_current_user_info

      result = gh_get_current_user_info()
      assert "error" in result
      assert "An unexpected error occurred" in result["error"]


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_rate_limit_exceeded(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_user.side_effect = RateLimitExceededException(
        403, {"message": "API rate limit exceeded"}
      )
      mock_init_client.return_value = mock_client
      from devops_mcps.github import gh_get_current_user_info

      result = gh_get_current_user_info()
    assert "error" in result
    assert "rate limit" in result["error"].lower()


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_github_exception(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_user.side_effect = GithubException(
        500, {"message": "Internal error"}
      )
      mock_init_client.return_value = mock_client
      from devops_mcps.github import gh_get_current_user_info

      result = gh_get_current_user_info()
      assert "error" in result
      assert "GitHub API Error" in result["error"]


@patch("devops_mcps.utils.github.github_user_api.logger")
@patch("devops_mcps.utils.github.github_user_api.cache")
def test_gh_get_current_user_info_unexpected_exception(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_user_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_user.side_effect = Exception("Unexpected failure")
      mock_init_client.return_value = mock_client
      from devops_mcps.github import gh_get_current_user_info

      result = gh_get_current_user_info()
      assert "error" in result
      assert "unexpected error" in result["error"].lower()


# --- Tests for gh_get_issue_details ---


@patch("devops_mcps.utils.github.github_issue_api.logger")
@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_get_issue_details_success(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test successful issue details retrieval."""
  with patch(
    "devops_mcps.utils.github.github_issue_api.initialize_github_client"
  ) as mock_init_client:
    mock_client = Mock()
    mock_issue = Mock()
    mock_issue.title = "Test Issue"
    mock_issue.body = "Issue description"
    mock_issue.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"

    # Mock labels
    mock_label = Mock()
    mock_label.name = "bug"
    mock_issue.labels = [mock_label]

    # Mock comments
    mock_comment = Mock()
    mock_comment.body = "Test comment"
    mock_issue.get_comments.return_value = [mock_comment]

    mock_client.get_issue.return_value = mock_issue
    mock_init_client.return_value = mock_client

    from devops_mcps.github import gh_get_issue_details

    result = gh_get_issue_details("owner", "repo", 1)
    assert result["title"] == "Test Issue"
    assert result["description"] == "Issue description"
    assert result["labels"] == ["bug"]
    assert result["comments"] == ["Test comment"]
    assert result["timestamp"] == "2023-01-01T00:00:00Z"


@patch("devops_mcps.utils.github.github_issue_api.logger")
@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_get_issue_details_cached(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = {
    "id": 1,
    "title": "Cached Issue",
    "body": "Cached body",
    "state": "open",
  }
  mock_cache_patch.set.return_value = None
  """Test cached issue details retrieval."""
  cached_data = {
    "title": "Cached Issue",
    "description": "Cached description",
    "labels": ["cached"],
    "comments": ["Cached comment"],
    "timestamp": "2023-01-01T00:00:00Z",
  }
  mock_cache_patch.get.return_value = cached_data

  from devops_mcps.github import gh_get_issue_details

  result = gh_get_issue_details("owner", "repo", 1)
  assert result == cached_data
  mock_cache_patch.get.assert_called_once()


@patch("devops_mcps.utils.github.github_issue_api.logger")
@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_get_issue_details_no_client(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test issue details retrieval when client not initialized."""
  with patch(
    "devops_mcps.utils.github.github_issue_api.initialize_github_client"
  ) as mock_init_client:
    mock_init_client.return_value = None

    from devops_mcps.github import gh_get_issue_details

    result = gh_get_issue_details("owner", "repo", 1)
    assert "error" in result
    assert (
      "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
      in result["error"]
    )


@patch("devops_mcps.utils.github.github_issue_api.logger")
@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_get_issue_details_github_exception(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test issue details retrieval with GitHub API error."""
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_issue_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_issue.side_effect = GithubException(
        404, {"message": "Not Found"}, {}
      )
      mock_init_client.return_value = mock_client

      from devops_mcps.github import gh_get_issue_details

      result = gh_get_issue_details("owner", "repo", 1)
      assert "error" in result
      assert "GitHub API Error" in result["error"]
      assert "404" in result["error"]


@patch("devops_mcps.utils.github.github_issue_api.logger")
@patch("devops_mcps.utils.github.github_issue_api.cache")
def test_gh_get_issue_details_unexpected_error(mock_cache_patch, mock_logger):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test issue details retrieval with unexpected error."""
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_issue_api.initialize_github_client"
    ) as mock_init_client:
      mock_client = Mock()
      mock_client.get_issue.side_effect = Exception("Unexpected error")
      mock_init_client.return_value = mock_client

      from devops_mcps.github import gh_get_issue_details

      result = gh_get_issue_details("owner", "repo", 1)
      assert "error" in result
      assert "An unexpected error occurred" in result["error"]


# Tests for gh_get_issue_content function
def test_gh_get_issue_content_success(mock_github_api):
  """Test gh_get_issue_content with successful response."""
  from unittest.mock import Mock

  # Mock issue object
  mock_issue = Mock()
  mock_issue.title = "Test Issue"
  mock_issue.body = "Issue description"
  mock_issue.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"
  mock_issue.updated_at.isoformat.return_value = "2023-01-02T00:00:00Z"

  # Mock labels
  mock_label = Mock()
  mock_label.name = "bug"
  mock_issue.labels = [mock_label]

  # Mock assignees
  mock_assignee = Mock()
  mock_assignee.login = "assignee1"
  mock_issue.assignees = [mock_assignee]

  # Mock creator
  mock_user = Mock()
  mock_user.login = "creator1"
  mock_issue.user = mock_user

  # Mock comments
  mock_comment = Mock()
  mock_comment.body = "Test comment"
  mock_comment.user.login = "commenter1"
  mock_comment.created_at.isoformat.return_value = "2023-01-01T12:00:00Z"
  mock_issue.get_comments.return_value = [mock_comment]

  # Mock repository
  mock_repo = Mock()
  mock_repo.get_issue.return_value = mock_issue
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_issue_content("owner", "repo", 1)

  assert result["title"] == "Test Issue"
  assert result["description"] == "Issue description"
  assert result["labels"] == ["bug"]
  assert len(result["comments"]) == 1
  assert result["comments"][0] == "Test comment"
  assert result["timestamp"] is not None


@patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"})
@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_no_client(mock_init_client, mock_cache_patch):
  """Test gh_get_issue_content when GitHub client is not initialized."""
  mock_cache_patch.get.return_value = None  # No cached result
  mock_init_client.return_value = None

  result = gh_get_issue_content("owner", "repo", 1)
  assert "error" in result
  assert (
    "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    in result["error"]
  )


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_issue_not_found(mock_init_client, mock_cache_patch):
  """Test gh_get_issue_content when issue is not found."""
  from github import UnknownObjectException

  mock_cache_patch.get.return_value = None  # No cached result
  mock_client = Mock()
  mock_repo = Mock()
  mock_repo.get_issue.side_effect = UnknownObjectException(404, "Not Found")
  mock_client.get_repo.return_value = mock_repo
  mock_init_client.return_value = mock_client

  result = gh_get_issue_content("owner", "repo", 999)

  assert "error" in result
  assert "Repository 'owner/repo' or issue #999 not found." in result["error"]


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_github_exception(mock_init_client, mock_cache_patch):
  """Test gh_get_issue_content with GitHub API exception."""
  from github import GithubException

  mock_cache_patch.get.return_value = None  # No cached result
  mock_client = Mock()
  mock_repo = Mock()
  mock_repo.get_issue.side_effect = GithubException(403, {"message": "Forbidden"})
  mock_client.get_repo.return_value = mock_repo
  mock_init_client.return_value = mock_client

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert "GitHub API Error: 403 - Forbidden" in result["error"]


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_unexpected_error(mock_init_client, mock_cache_patch):
  """Test gh_get_issue_content with unexpected error."""
  mock_cache_patch.get.return_value = None  # No cached result
  mock_client = Mock()
  mock_client.get_repo.side_effect = Exception("Unexpected error")
  mock_init_client.return_value = mock_client

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert "An unexpected error occurred: Unexpected error" in result["error"]


# Additional tests for gh_get_file_contents binary handling
def test_gh_get_file_contents_binary_decode_error(mock_github_api):
  """Test gh_get_file_contents with binary file that can't be decoded."""
  from unittest.mock import Mock

  # Create mock contents that will raise UnicodeDecodeError
  mock_contents = Mock()
  mock_contents.encoding = "base64"
  mock_contents.content = "some_content"
  mock_contents.name = "binary_file.bin"
  mock_contents.path = "path/to/binary_file.bin"
  mock_contents.size = 1024
  mock_contents.sha = "abc123"
  mock_contents.type = "file"
  mock_contents.html_url = "https://github.com/owner/repo/blob/main/binary_file.bin"

  # Create a mock object that raises UnicodeDecodeError when decode is called
  class MockDecodedContent:
    def decode(self, encoding):
      raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

  mock_contents.decoded_content = MockDecodedContent()

  # Mock the _to_dict to always return a dictionary
  mock_metadata = {
    "name": "binary_file.bin",
    "path": "path/to/binary_file.bin",
    "size": 1024,
    "sha": "abc123",
    "type": "file",
    "html_url": "https://github.com/owner/repo/blob/main/binary_file.bin",
  }

  with patch(
    "devops_mcps.utils.github.github_repository_api._to_dict",
    return_value=mock_metadata,
  ):
    mock_repo = Mock()
    mock_repo.get_contents.return_value = mock_contents
    mock_github_api.get_repo.return_value = mock_repo

    result = gh_get_file_contents("owner", "repo", "path/to/binary_file.bin")

    assert "error" in result
    assert "Could not decode content" in result["error"]


def test_gh_get_file_contents_empty_content(mock_github_api):
  """Test gh_get_file_contents with empty content."""
  from unittest.mock import Mock

  mock_contents = Mock()
  mock_contents.encoding = "base64"
  mock_contents.content = None
  mock_contents.name = "empty_file.txt"
  mock_contents.path = "path/to/empty_file.txt"
  mock_contents.size = 0
  mock_contents.sha = "def456"
  mock_contents.type = "file"
  mock_contents.html_url = "https://github.com/owner/repo/blob/main/empty_file.txt"

  # Mock the _to_dict behavior for this object
  def mock_to_dict_side_effect(obj):
    if obj is mock_contents:
      return {
        "name": "empty_file.txt",
        "path": "path/to/empty_file.txt",
        "size": 0,
        "sha": "def456",
        "type": "file",
        "html_url": "https://github.com/owner/repo/blob/main/empty_file.txt",
      }
    return {}  # Return empty dict instead of obj to avoid Mock issues

  with patch(
    "devops_mcps.utils.github.github_repository_api._to_dict",
    side_effect=mock_to_dict_side_effect,
  ):
    mock_repo = Mock()
    mock_repo.get_contents.return_value = mock_contents
    mock_github_api.get_repo.return_value = mock_repo

    result = gh_get_file_contents("owner", "repo", "path/to/empty_file.txt")

    assert "message" in result
    assert "File appears to be empty" in result["message"]


def test_gh_get_file_contents_non_base64_content(mock_github_api):
  """Test gh_get_file_contents with non-base64 content."""
  from unittest.mock import Mock

  mock_contents = Mock()
  mock_contents.encoding = "utf-8"
  mock_contents.content = "Raw file content"
  mock_contents.name = "raw_file.txt"
  mock_contents.path = "path/to/raw_file.txt"

  mock_repo = Mock()
  mock_repo.get_contents.return_value = mock_contents
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_file_contents("owner", "repo", "path/to/raw_file.txt")

  assert result == "Raw file content"


# Additional tests for gh_search_code error handling
def test_gh_search_code_authentication_error(mock_github_api):
  """Test gh_search_code with authentication error."""
  from github import GithubException

  mock_github_api.search_code.side_effect = GithubException(
    401, {"message": "Bad credentials"}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "Authentication required" in result["error"]


def test_gh_search_code_invalid_query_error(mock_github_api):
  """Test gh_search_code with invalid query error."""
  from github import GithubException

  mock_github_api.search_code.side_effect = GithubException(
    422, {"message": "Validation Failed"}
  )

  result = gh_search_code("invalid query")

  assert "error" in result
  assert "Invalid search query" in result["error"]


def test_gh_search_code_unexpected_error(mock_github_api):
  """Test gh_search_code with unexpected error."""
  mock_github_api.search_code.side_effect = Exception("Network error")

  result = gh_search_code("test query")

  assert "error" in result
  assert "unexpected error occurred" in result["error"]


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_no_client(mock_cache_patch):
  """Test gh_search_code when GitHub client is not initialized."""
  mock_cache_patch.get.return_value = None  # No cached result

  with patch(
    "devops_mcps.utils.github.github_search_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_search_code("test query")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_with_custom_sort_and_order(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code with custom sort and order parameters."""
  mock_instance = mock_github_api
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 5

  # Mock ContentFile item
  mock_code_item = Mock(spec=ContentFile)
  mock_code_item.type = "file"
  mock_code_item.name = "test.py"
  mock_code_item.path = "test.py"
  mock_code_item.size = 1024
  mock_code_item.html_url = "https://github.com/test/repo/blob/main/test.py"
  mock_code_item.repository = Mock()
  mock_code_item.repository.full_name = "test/repo"

  mock_code_results.get_page.return_value = [mock_code_item]
  mock_instance.search_code.return_value = mock_code_results

  with patch(
    "devops_mcps.utils.github.github_client.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = mock_instance

    result = gh_search_code("function test", sort="updated", order="asc")

  assert isinstance(result, list)
  mock_instance.search_code.assert_called_once_with(
    query="function test", sort="updated", order="asc"
  )
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_cached_result(mock_cache_patch, mock_github):
  mock_cache_patch.get.return_value = [
    {"name": "cached_file.py", "repository": {"full_name": "user/repo"}}
  ]
  mock_cache_patch.set.return_value = None
  """Test gh_search_code returns cached result when available."""
  cached_data = [{"path": "cached_file.py", "score": 1.0}]
  mock_cache_patch.get.return_value = cached_data

  result = gh_search_code("cached query")

  assert result == cached_data
  # Ensure GitHub API is not called when cache hit
  mock_github.assert_not_called()


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_cache_miss(mock_cache_patch, mock_github_api):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code when cache miss occurs."""

  mock_instance = mock_github_api
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 3

  # Mock ContentFile object for code search result
  mock_code_item = Mock(spec=ContentFile)
  mock_code_item.type = "file"
  mock_code_item.name = "new_file.py"
  mock_code_item.path = "new_file.py"
  mock_code_item.size = 1024
  mock_code_item.html_url = "https://github.com/owner/repo/blob/main/new_file.py"
  mock_code_item.repository = Mock()
  mock_code_item.repository.full_name = "owner/repo"

  mock_code_results.get_page.return_value = [mock_code_item]
  mock_instance.search_code.return_value = mock_code_results

  with patch(
    "devops_mcps.utils.github.github_client.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = mock_instance
    result = gh_search_code("new query")

  expected_result = [
    {
      "type": "file",
      "name": "new_file.py",
      "path": "new_file.py",
      "size": 1024,
      "html_url": "https://github.com/owner/repo/blob/main/new_file.py",
      "repository_full_name": "owner/repo",
    }
  ]
  assert result == expected_result
  mock_cache_patch.get.assert_called_once()
  mock_cache_patch.set.assert_called_once_with(
    "github:search_code:new query:indexed:desc", expected_result, ttl=300
  )


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_forbidden_error(mock_cache_patch, mock_github_api):
  """Test gh_search_code with 403 Forbidden error."""
  from github import GithubException

  mock_cache_patch.get.return_value = None  # No cached result
  mock_github_api.search_code.side_effect = GithubException(
    403, {"message": "API rate limit exceeded"}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "Authentication required or insufficient permissions" in result["error"]


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_github_exception_other_status(
  mock_cache_patch, mock_github_api
):
  """Test gh_search_code with other GitHub exception status codes."""
  from github import GithubException

  mock_cache_patch.get.return_value = None  # No cached result
  mock_github_api.search_code.side_effect = GithubException(
    500, {"message": "Internal server error"}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "GitHub API Error: 500" in result["error"]
  assert "Internal server error" in result["error"]


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_github_exception_no_message(mock_cache_patch, mock_github_api):
  """Test gh_search_code with GitHub exception that has no message."""
  from github import GithubException

  mock_cache_patch.get.return_value = None  # No cached result
  mock_github_api.search_code.side_effect = GithubException(
    404,
    {},  # No message in data
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "GitHub API Error: 404" in result["error"]
  assert "Unknown GitHub error" in result["error"]


@patch("devops_mcps.utils.github.github_search_api.initialize_github_client")
@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_empty_results(mock_cache_patch, mock_init_client, mock_github):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code with empty search results."""
  mock_instance = mock_github.return_value
  mock_init_client.return_value = mock_instance
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 0
  mock_code_results.get_page.return_value = []
  mock_instance.search_code.return_value = mock_code_results

  result = gh_search_code("nonexistent code")

  assert isinstance(result, list)
  assert len(result) == 0
  mock_cache_patch.set.assert_called_once()


def test_gh_search_code_input_validation():
  """Test gh_search_code with various input parameters."""
  from devops_mcps.inputs import SearchCodeInput

  # Test valid inputs
  valid_input = SearchCodeInput(q="test", sort="indexed", order="desc")
  assert valid_input.q == "test"
  assert valid_input.sort == "indexed"
  assert valid_input.order == "desc"

  # Test default values
  default_input = SearchCodeInput(q="test")
  assert default_input.sort == "indexed"
  assert default_input.order == "desc"

  # Test invalid order should raise ValueError
  with pytest.raises(ValueError, match="order must be 'asc' or 'desc'"):
    SearchCodeInput(q="test", order="invalid")


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_logging(mock_cache_patch, mock_github_api, caplog):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code logging behavior."""
  import logging

  caplog.set_level(logging.DEBUG)

  mock_instance = mock_github_api
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 2

  # Mock code items with proper attributes
  mock_code_item1 = Mock(spec=ContentFile)
  mock_code_item1.type = "file"
  mock_code_item1.name = "test1.py"
  mock_code_item1.path = "test1.py"
  mock_code_item1.size = 1024

  mock_code_item1.repository.full_name = "owner/repo1"
  mock_code_item1.html_url = "https://github.com/owner/repo1/blob/main/test1.py"

  mock_code_item2 = Mock(spec=ContentFile)
  mock_code_item2.type = "file"
  mock_code_item2.name = "test2.py"
  mock_code_item2.path = "test2.py"
  mock_code_item2.size = 512

  mock_code_item2.repository.full_name = "owner/repo2"
  mock_code_item2.html_url = "https://github.com/owner/repo2/blob/main/test2.py"

  mock_code_results.get_page.return_value = [mock_code_item1, mock_code_item2]
  mock_instance.search_code.return_value = mock_code_results

  with patch(
    "devops_mcps.utils.github.github_client.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = mock_instance

    with caplog.at_level(logging.DEBUG):
      gh_search_code("test logging")

  # Check debug logs
  assert "gh_search_code called with query: 'test logging'" in caplog.text
  assert "Found 2 code results matching query" in caplog.text


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_cache_key_generation(mock_cache_patch, mock_github):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code generates correct cache keys."""
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.get_page.return_value = []
  mock_instance.search_code.return_value = mock_code_results

  with patch(
    "devops_mcps.utils.github.github_client.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = mock_instance

    # Test with different parameters
    gh_search_code("query1", "updated", "asc")
    gh_search_code("query2", "indexed", "desc")

  # Verify cache keys
  expected_calls = [
    call("github:search_code:query1:updated:asc"),
    call("github:search_code:query2:indexed:desc"),
  ]
  mock_cache_patch.get.assert_has_calls(expected_calls)


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_force_client_initialization(mock_cache_patch):
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  """Test gh_search_code calls initialize_github_client with force=True."""
  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "fake_token"}):
    with patch(
      "devops_mcps.utils.github.github_search_api.initialize_github_client"
    ) as mock_init:
      mock_client = Mock()
      mock_code_results = Mock(spec=PaginatedList)
      mock_code_results.totalCount = 0
      mock_code_results.get_page.return_value = []
      mock_client.search_code.return_value = mock_code_results
      mock_init.return_value = mock_client

      gh_search_code("test")

      mock_init.assert_called_once_with(force=True)


# --- Additional Tests for Missing Coverage ---


def test_initialize_github_client_with_custom_api_url_env():
  """Test initialization with custom GitHub API URL from environment."""
  with patch.dict(
    "os.environ",
    {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "test_token",
      "GITHUB_API_URL": "https://github.enterprise.com/api/v3",
    },
  ):
    with patch("devops_mcps.utils.github_client.Github") as mock_github:
      mock_instance = mock_github.return_value
      mock_instance.get_user.return_value.login = "test_user"

      client = initialize_github_client(force=True)

      # Verify custom base_url was used
      mock_github.assert_called_once()
      call_kwargs = mock_github.call_args[1]
      assert call_kwargs["base_url"] == "https://github.enterprise.com/api/v3"
      assert client is not None


def test_initialize_github_client_already_initialized():
  """Test that client returns existing instance when already initialized."""
  with patch("devops_mcps.utils.github_client.Github") as mock_github:
    with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
      mock_client = MagicMock()
      mock_user = MagicMock()
      mock_user.login = "test_user"
      mock_client.get_user.return_value = mock_user
      mock_github.return_value = mock_client

      # First call to initialize
      client1 = initialize_github_client(force=True)

      # Second call should return existing client without creating new one
      client2 = initialize_github_client(force=False)

      # Both should be the same instance
      assert client1 is client2
      assert client1 is mock_client
      # Github should only be called once (for the first initialization)
      mock_github.assert_called_once()


def test_gh_get_current_user_info_no_token():
  """Test gh_get_current_user_info when no GitHub token is provided."""
  with patch.dict("os.environ", {}, clear=True):
    result = gh_get_current_user_info()

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in result["error"]


def test_gh_get_file_contents_file_too_large(mock_github_api, mock_env_vars):
  """Test file content retrieval when file is too large."""
  mock_repo = MagicMock()
  mock_repo.get_contents.side_effect = GithubException(
    413, {"message": "File too large to retrieve"}, {}
  )
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_file_contents("owner", "repo", "large_file.txt")

  assert "error" in result
  assert "too large" in result["error"]


def test_gh_list_commits_empty_repository(mock_github_api, mock_env_vars):
  """Test commit listing when repository is empty."""
  mock_repo = MagicMock()
  mock_repo.get_commits.side_effect = GithubException(
    409, {"message": "Git Repository is empty"}, {}
  )
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_commits("owner", "empty-repo")

  assert "error" in result
  assert "empty" in result["error"]


def test_gh_list_commits_branch_not_found(mock_github_api, mock_env_vars):
  """Test commit listing when branch doesn't exist."""
  mock_repo = MagicMock()
  mock_repo.get_commits.side_effect = GithubException(
    404, {"message": "Branch not found"}, {}
  )
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_commits("owner", "repo", branch="nonexistent-branch")

  assert "error" in result
  assert "not found" in result["error"]


def test_gh_list_commits_sha_not_found(mock_github_api, mock_env_vars):
  """Test commit listing when SHA doesn't exist."""
  mock_repo = MagicMock()
  mock_repo.get_commits.side_effect = GithubException(
    422, {"message": "No commit found for SHA: abc123"}, {}
  )
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_commits("owner", "repo", branch="abc123")

  assert "error" in result
  assert "not found" in result["error"]


def test_to_dict_fallback_with_raw_data_mock():
  """Test _to_dict fallback handling with mock objects containing _rawData."""
  mock_obj = MagicMock()
  mock_obj._rawData = {"name": "test", "value": 123}

  result = _to_dict(mock_obj)

  assert isinstance(result, dict)
  assert "name" in result or "test" in str(result)


def test_to_dict_fallback_error_handling():
  """Test _to_dict fallback error handling when serialization fails."""

  class ProblematicObject:
    def __getattribute__(self, name):
      if name in ["__class__", "__dict__"]:
        return object.__getattribute__(self, name)
      raise Exception("Attribute access failed")

  obj = ProblematicObject()
  result = _to_dict(obj)

  assert isinstance(result, str)
  assert "Error serializing" in result or "Object of type" in result


def test_to_dict_mock_object_fallback():
  """Test _to_dict handling of mock objects without _rawData."""
  mock_obj = MagicMock()
  mock_obj.name = "test_name"
  mock_obj.full_name = "test/repo"
  mock_obj.description = "test description"
  # Remove _rawData to test fallback
  del mock_obj._rawData

  result = _to_dict(mock_obj)

  # Should return either the mock attributes or a string representation
  assert isinstance(result, (dict, str))
  if isinstance(result, dict):
    assert len(result) > 0  # Should have some attributes


def test_handle_paginated_list_error_handling():
  """Test _handle_paginated_list error handling."""
  mock_paginated = MagicMock()
  mock_paginated.get_page.side_effect = Exception("API Error")

  result = _handle_paginated_list(mock_paginated)

  assert isinstance(result, list)
  assert len(result) == 1
  assert "error" in result[0]
  assert "Failed to process results" in result[0]["error"]


def test_gh_search_repositories_no_client():
  """Test repository search when GitHub client is not initialized."""
  with patch(
    "devops_mcps.utils.github.github_search_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_search_repositories("test query")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_file_contents_no_client():
  """Test file content retrieval when GitHub client is not initialized."""
  with patch(
    "devops_mcps.utils.github.github_repository_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_get_file_contents("owner", "repo", "path")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_list_commits_no_client():
  """Test commit listing when GitHub client is not initialized."""
  with patch(
    "devops_mcps.utils.github.github_commit_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_list_commits("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_list_issues_no_client():
  """Test issue listing when GitHub client is not initialized."""
  with patch(
    "devops_mcps.utils.github.github_issue_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_list_issues("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_repository_no_client():
  """Test repository retrieval when GitHub client is not initialized."""
  with patch(
    "devops_mcps.utils.github.github_repository_api.initialize_github_client"
  ) as mock_init:
    mock_init.return_value = None

    result = gh_get_repository("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_current_user_info_client_not_initialized():
  """Test gh_get_current_user_info when client initialization fails."""
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
    with patch(
      "devops_mcps.utils.github.github_client.initialize_github_client"
    ) as mock_init:
      mock_init.return_value = None

      result = gh_get_current_user_info()

      assert "error" in result
      assert "GitHub client not initialized" in result["error"]


def test_gh_list_issues_unexpected_error(mock_github_api, mock_env_vars):
  """Test issue listing when unexpected error occurs."""
  mock_repo = MagicMock()
  mock_repo.get_issues.side_effect = Exception("Unexpected error")
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_issues("owner", "repo")

  assert "error" in result
  assert "unexpected error" in result["error"].lower()


def test_gh_get_repository_unexpected_error(mock_github_api, mock_env_vars):
  """Test repository retrieval when unexpected error occurs."""
  mock_github_api.get_repo.side_effect = Exception("Unexpected error")

  result = gh_get_repository("owner", "repo")

  assert "error" in result
  assert "unexpected error" in result["error"].lower()


def test_gh_search_repositories_unexpected_error(mock_github_api, mock_env_vars):
  """Test repository search when unexpected error occurs."""
  mock_github_api.search_repositories.side_effect = Exception("Unexpected error")

  result = gh_search_repositories("test query")

  assert "error" in result
  assert "unexpected error" in result["error"].lower()


def test_gh_get_file_contents_unexpected_error(mock_github_api, mock_env_vars):
  """Test file content retrieval when unexpected error occurs."""
  mock_repo = MagicMock()
  mock_repo.get_contents.side_effect = Exception("Unexpected error")
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_file_contents("owner", "repo", "path")

  assert "error" in result
  assert "unexpected error" in result["error"].lower()


def test_gh_list_commits_unexpected_error(mock_github_api, mock_env_vars):
  """Test commit listing when unexpected error occurs."""
  mock_repo = MagicMock()
  mock_repo.get_commits.side_effect = Exception("Unexpected error")
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_list_commits("owner", "repo")

  assert "error" in result
  assert "unexpected error" in result["error"].lower()


def test_to_dict_git_author_no_date():
  """Test _to_dict with GitAuthor object that has no date."""
  from github.GitAuthor import GitAuthor

  mock_author = MagicMock(spec=GitAuthor)
  mock_author.name = "Test Author"
  mock_author.date = None

  result = _to_dict(mock_author)

  assert isinstance(result, dict)
  assert result["name"] == "Test Author"
  assert result["date"] is None


def test_to_dict_license_object():
  """Test _to_dict with License object."""
  from github.License import License

  mock_license = MagicMock(spec=License)
  mock_license.name = "MIT License"
  mock_license.spdx_id = "MIT"

  result = _to_dict(mock_license)

  assert isinstance(result, dict)
  assert result["name"] == "MIT License"
  assert result["spdx_id"] == "MIT"


def test_to_dict_milestone_object():
  """Test _to_dict with Milestone object."""
  from github.Milestone import Milestone

  mock_milestone = MagicMock(spec=Milestone)
  mock_milestone.title = "v1.0.0"
  mock_milestone.state = "open"

  result = _to_dict(mock_milestone)

  assert isinstance(result, dict)
  assert result["title"] == "v1.0.0"
  assert result["state"] == "open"


def test_to_dict_content_file_object():
  """Test _to_dict with ContentFile object."""
  from github.ContentFile import ContentFile

  mock_content = MagicMock(spec=ContentFile)
  mock_content.name = "test.py"
  mock_content.path = "src/test.py"
  mock_content.type = "file"

  result = _to_dict(mock_content)

  assert isinstance(result, dict)
  assert result["name"] == "test.py"
  assert result["path"] == "src/test.py"
  assert result["type"] == "file"


def test_to_dict_unknown_object_fallback():
  """Test _to_dict fallback for unknown object types."""

  class UnknownObject:
    def __init__(self):
      self.some_attr = "value"

  obj = UnknownObject()
  result = _to_dict(obj)

  assert isinstance(result, str)
  assert "Object of type UnknownObject" in result


def test_initialize_github_client_exception_during_auth(mock_github, mock_logger):
  """Test initialization when exception occurs during authentication."""
  mock_instance = mock_github.return_value
  mock_instance.get_user.side_effect = Exception("Connection error")

  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
    client = initialize_github_client(force=True)

  assert client is None
  mock_logger.error.assert_called()


@patch("devops_mcps.utils.github.github_search_api.cache")
def test_gh_search_code_rate_limit_exceeded(
  mock_cache_patch, mock_github_api, mock_env_vars
):
  """Test code search when rate limit is exceeded."""
  mock_cache_patch.get.return_value = None  # No cached result
  mock_github_api.search_code.side_effect = RateLimitExceededException(
    403, {"message": "API rate limit exceeded"}, {}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "403" in result["error"] or "rate limit" in result["error"].lower()


def test_gh_search_repositories_rate_limit_exceeded(mock_github_api, mock_env_vars):
  """Test repository search when rate limit is exceeded."""
  mock_github_api.search_repositories.side_effect = RateLimitExceededException(
    403, {"message": "API rate limit exceeded"}, {}
  )

  result = gh_search_repositories("test query")

  assert "error" in result
  assert "403" in result["error"]


def test_gh_get_file_contents_repository_not_found(mock_github_api, mock_env_vars):
  """Test file content retrieval when repository doesn't exist."""
  mock_github_api.get_repo.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}, {}
  )

  result = gh_get_file_contents("owner", "nonexistent-repo", "path")

  assert "error" in result
  assert "not found" in result["error"].lower()


def test_gh_list_commits_repository_not_found(mock_github_api, mock_env_vars):
  """Test commit listing when repository doesn't exist."""
  mock_github_api.get_repo.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}, {}
  )

  result = gh_list_commits("owner", "nonexistent-repo")

  assert "error" in result
  assert "not found" in result["error"].lower()


def test_gh_list_issues_repository_not_found(mock_github_api, mock_env_vars):
  """Test issue listing when repository doesn't exist."""
  mock_github_api.get_repo.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}, {}
  )

  result = gh_list_issues("owner", "nonexistent-repo")

  assert "error" in result
  assert "not found" in result["error"].lower()


# Additional tests for github_repository_api.py coverage improvement


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_unicode_decode_error(mock_cache_patch, mock_github_api):
  """Test file content retrieval with UnicodeDecodeError."""
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_content = Mock(spec=ContentFile)
  mock_content.type = "file"
  mock_content.encoding = "base64"
  mock_content.content = "dGVzdCBjb250ZW50"  # "test content" in base64
  mock_content.decoded_content = b"\xff\xfe"  # Invalid UTF-8 bytes
  mock_content.size = 100
  mock_content.name = "binary_file.bin"
  mock_content.path = "path/to/binary_file.bin"
  mock_content._rawData = {
    "type": "file",
    "encoding": "base64",
    "content": "dGVzdCBjb250ZW50",
    "path": "path/to/binary_file.bin",
    "size": 100,
    "name": "binary_file.bin",
  }
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = mock_content

  result = gh_get_file_contents("owner", "repo", "path/to/binary_file.bin")

  assert isinstance(result, dict)
  assert "error" in result
  assert "Could not decode content (likely binary file)" in result["error"]
  assert "type" in result
  assert "size" in result


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_decode_exception(mock_cache_patch, mock_github_api):
  """Test file content retrieval with general decode exception."""
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_content = Mock(spec=ContentFile)
  mock_content.type = "file"
  mock_content.encoding = "base64"
  mock_content.content = "dGVzdCBjb250ZW50"
  # Mock decoded_content to raise a general exception
  mock_content.decoded_content = property(
    lambda self: exec('raise Exception("Decode error")')
  )
  mock_content.size = 100
  mock_content.name = "problematic_file.txt"
  mock_content.path = "path/to/problematic_file.txt"
  mock_content._rawData = {
    "type": "file",
    "encoding": "base64",
    "content": "dGVzdCBjb250ZW50",
    "path": "path/to/problematic_file.txt",
    "size": 100,
    "name": "problematic_file.txt",
  }
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = mock_content

  result = gh_get_file_contents("owner", "repo", "path/to/problematic_file.txt")

  assert isinstance(result, dict)
  assert "error" in result
  assert "Error decoding content" in result["error"]
  assert "type" in result


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_empty_content(mock_cache_patch, mock_github_api):
  """Test file content retrieval with empty/None content."""
  mock_cache_patch.get.return_value = None
  mock_cache_patch.set.return_value = None
  mock_repo = Mock()
  mock_content = Mock(spec=ContentFile)
  mock_content.type = "file"
  mock_content.encoding = "base64"
  mock_content.content = None  # Empty content
  mock_content.size = 0
  mock_content.name = "empty_file.txt"
  mock_content.path = "path/to/empty_file.txt"
  mock_content._rawData = {
    "type": "file",
    "encoding": "base64",
    "content": None,
    "path": "path/to/empty_file.txt",
    "size": 0,
    "name": "empty_file.txt",
  }
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = mock_content

  result = gh_get_file_contents("owner", "repo", "path/to/empty_file.txt")

  assert isinstance(result, dict)
  assert "message" in result
  assert "File appears to be empty or content is inaccessible" in result["message"]
  assert "type" in result
  mock_cache_patch.set.assert_called_once()


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_file_contents_large_file_error(mock_cache_patch, mock_github_api):
  """Test file content retrieval with 'too large' GitHub error."""
  mock_cache_patch.get.return_value = None
  mock_repo = Mock()
  mock_github_api.get_repo.return_value = mock_repo
  mock_repo.get_contents.side_effect = GithubException(
    413, {"message": "File too large to retrieve via API"}, {}
  )

  result = gh_get_file_contents("owner", "repo", "path/to/large_file.zip")

  assert isinstance(result, dict)
  assert "error" in result
  assert "too large to retrieve via the API" in result["error"]


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_repository_github_exception(mock_cache_patch, mock_github_api):
  """Test repository retrieval with GitHub API exception."""
  mock_cache_patch.get.return_value = None
  mock_github_api.get_repo.side_effect = GithubException(
    500, {"message": "Internal server error"}, {}
  )

  result = gh_get_repository("owner", "repo")

  assert isinstance(result, dict)
  assert "error" in result
  assert "GitHub API Error: 500" in result["error"]
  assert "Internal server error" in result["error"]


@patch("devops_mcps.utils.github.github_repository_api.cache")
def test_gh_get_repository_unexpected_exception(mock_cache_patch, mock_github_api):
  """Test repository retrieval with unexpected exception."""
  mock_cache_patch.get.return_value = None
  mock_github_api.get_repo.side_effect = Exception("Unexpected error")

  result = gh_get_repository("owner", "repo")

  assert isinstance(result, dict)
  assert "error" in result
  assert "An unexpected error occurred: Unexpected error" in result["error"]


# Tests for legacy wrapper functions
@patch("devops_mcps.github.gh_search_repositories")
def test_search_repositories_wrapper(mock_gh_search):
  """Test search_repositories legacy wrapper function."""
  mock_gh_search.return_value = {"repositories": []}

  result = search_repositories("test query")

  mock_gh_search.assert_called_once_with("test query")
  assert result == {"repositories": []}


@patch("devops_mcps.github.gh_get_current_user_info")
def test_get_current_user_info_wrapper(mock_gh_get_user):
  """Test get_current_user_info legacy wrapper function."""
  mock_gh_get_user.return_value = {"login": "testuser"}

  result = get_current_user_info()

  mock_gh_get_user.assert_called_once()
  assert result == {"login": "testuser"}


@patch("devops_mcps.github.gh_get_file_contents")
def test_get_file_contents_wrapper(mock_gh_get_file):
  """Test get_file_contents legacy wrapper function."""
  mock_gh_get_file.return_value = {"content": "test content"}

  result = get_file_contents("owner", "repo", "path/to/file")

  mock_gh_get_file.assert_called_once_with("owner", "repo", "path/to/file", None)
  assert result == {"content": "test content"}


@patch("devops_mcps.github.gh_list_commits")
def test_list_commits_wrapper(mock_gh_list_commits):
  """Test list_commits legacy wrapper function."""
  mock_gh_list_commits.return_value = {"commits": []}

  result = list_commits("owner", "repo")

  mock_gh_list_commits.assert_called_once_with("owner", "repo", None)
  assert result == {"commits": []}


@patch("devops_mcps.github.gh_list_issues")
def test_list_issues_wrapper(mock_gh_list_issues):
  """Test list_issues legacy wrapper function."""
  mock_gh_list_issues.return_value = {"issues": []}

  result = list_issues("owner", "repo")

  mock_gh_list_issues.assert_called_once_with(
    "owner", "repo", "open", None, "created", "desc"
  )
  assert result == {"issues": []}


@patch("devops_mcps.github.gh_get_repository")
def test_get_repository_wrapper(mock_gh_get_repo):
  """Test get_repository legacy wrapper function."""
  mock_gh_get_repo.return_value = {"name": "test-repo"}

  result = get_repository("owner", "repo")

  mock_gh_get_repo.assert_called_once_with("owner", "repo")
  assert result == {"name": "test-repo"}


@patch("devops_mcps.github.gh_search_code")
def test_search_code_wrapper(mock_gh_search_code):
  """Test search_code legacy wrapper function."""
  mock_gh_search_code.return_value = {"code_results": []}

  result = search_code("test query")

  mock_gh_search_code.assert_called_once_with("test query", "indexed", "desc")
  assert result == {"code_results": []}


@patch("devops_mcps.github.gh_get_issue_details")
def test_get_issue_details_wrapper(mock_gh_get_issue):
  """Test get_issue_details legacy wrapper function."""
  mock_gh_get_issue.return_value = {"title": "Test Issue"}

  result = get_issue_details("owner", "repo", 1)

  mock_gh_get_issue.assert_called_once_with("owner", "repo", 1)
  assert result == {"title": "Test Issue"}


@patch("devops_mcps.github.gh_get_issue_content")
def test_get_github_issue_content_wrapper(mock_gh_get_issue):
  """Test get_github_issue_content legacy wrapper function."""
  mock_gh_get_issue.return_value = {"body": "Issue content"}

  result = get_github_issue_content("owner", "repo", 1)

  mock_gh_get_issue.assert_called_once_with("owner", "repo", 1)
  assert result == {"body": "Issue content"}


# Test error propagation through wrapper functions
@patch("devops_mcps.github.gh_search_repositories")
def test_search_repositories_wrapper_error_propagation(mock_gh_search):
  """Test search_repositories wrapper propagates errors correctly."""
  mock_gh_search.return_value = {"error": "API Error"}

  result = search_repositories("test query")

  mock_gh_search.assert_called_once_with("test query")
  assert result == {"error": "API Error"}


@patch("devops_mcps.github.gh_get_current_user_info")
def test_get_current_user_info_wrapper_error_propagation(mock_gh_get_user):
  """Test get_current_user_info wrapper propagates errors correctly."""
  mock_gh_get_user.return_value = {"error": "Authentication failed"}

  result = get_current_user_info()

  mock_gh_get_user.assert_called_once()
  assert result == {"error": "Authentication failed"}
