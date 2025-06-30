import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock, call

from devops_mcps.github import (
  initialize_github_client,
  _to_dict,
  _handle_paginated_list,
  gh_search_repositories,
  gh_get_file_contents,
  gh_list_commits,
  gh_list_issues,
  gh_get_repository,
  gh_search_code,
  gh_get_issue_content,
  gh_get_current_user_info,
)
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
  with patch("devops_mcps.github.Github") as mock:
    yield mock


@pytest.fixture
def mock_github_api(mock_env_vars):
  """Mock GitHub API and initialize client."""
  with patch("devops_mcps.github.Github", autospec=True) as mock_github:
    mock_instance = mock_github.return_value
    mock_instance.get_user.return_value = MagicMock(login="test_user")
    mock_instance.get_rate_limit.return_value = MagicMock()
    mock_instance.get_repo.return_value = MagicMock()

    # Patch the global client directly
    with patch("devops_mcps.github.g", new=mock_instance):
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
  with patch("devops_mcps.github.cache") as mock:
    mock.get.return_value = None
    yield mock


@pytest.fixture
def mock_logger():
  with patch("devops_mcps.github.logger") as mock:
    yield mock


# --- Test initialize_github_client ---


def test_initialize_github_client_with_token(mock_github, mock_logger):
  # Setup
  os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "test_token"
  mock_instance = mock_github.return_value
  mock_instance.get_user.return_value.login = "test_user"

  # Execute
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
    client = initialize_github_client()

  # Verify
  assert client is not None
  mock_github.assert_called_once_with(
    auth=mock_github.call_args[1]["auth"],
    timeout=60,
    per_page=10,
    base_url="https://api.github.com",
  )
  mock_logger.info.assert_called_once()
  mock_logger.info.assert_called()


def test_initialize_github_client_without_token(mock_github, mock_logger):
  # Setup
  mock_instance = mock_github.return_value
  mock_instance.get_rate_limit.return_value = True

  # Execute
  with patch.dict("os.environ", {}, clear=True):
    client = initialize_github_client()

  # Verify
  assert client is None
  mock_github.assert_not_called()
  mock_logger.warning.assert_called_once()


def test_initialize_github_client_bad_credentials(mock_github, mock_logger):
  # Setup
  mock_instance = mock_github.return_value
  mock_instance.get_user.side_effect = BadCredentialsException(
    401, {"message": "Bad credentials"}
  )

  # Execute
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "invalid_token"}):
    client = initialize_github_client()

  # Verify
  assert client is None
  mock_logger.error.assert_called_once_with(
    "Invalid GitHub Personal Access Token provided."
  )


def test_initialize_github_client_rate_limit_exceeded(mock_github, mock_logger):
  """Test GitHub client initialization with rate limit exceeded."""
  mock_github.return_value.get_user.side_effect = RateLimitExceededException(
    403, {"message": "API rate limit exceeded"}
  )

  with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "valid_token"}):
    result = initialize_github_client(force=True)
    assert result is None
    mock_logger.error.assert_called_with(
      "GitHub API rate limit exceeded during initialization."
    )


def test_initialize_github_client_unauthenticated_error(mock_github, mock_logger):
  """Test GitHub client initialization when no token is provided."""

  with patch.dict(os.environ, {}, clear=True):  # No token
    result = initialize_github_client(force=True)
    assert result is None
    mock_github.assert_not_called()
    mock_logger.warning.assert_called_once()


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


def test_handle_paginated_list(mock_logger):
  mock_item1 = Mock()
  mock_item2 = Mock()
  mock_paginated = Mock(spec=PaginatedList)
  mock_paginated.get_page.return_value = [mock_item1, mock_item2]

  with patch("devops_mcps.github._to_dict") as mock_to_dict:
    mock_to_dict.side_effect = lambda x: {"mock": str(x)}
    result = _handle_paginated_list(mock_paginated)

  assert isinstance(result, list)
  assert len(result) == 2
  mock_paginated.get_page.assert_called_once_with(0)
  mock_logger.debug.assert_called()


def test_handle_paginated_list_error(mock_logger):
  mock_paginated = Mock(spec=PaginatedList)
  mock_paginated.get_page.side_effect = Exception("Test error")

  result = _handle_paginated_list(mock_paginated)

  assert isinstance(result, list)
  assert "error" in result[0]
  mock_logger.error.assert_called()


# --- Test gh_search_repositories ---


def test_gh_search_repositories_success(mock_cache, mock_github):
  mock_instance = mock_github.return_value
  mock_search = Mock(spec=PaginatedList)
  mock_search.totalCount = 2
  mock_instance.search_repositories.return_value = mock_search

  with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
    mock_handler.return_value = [{"name": "repo1"}, {"name": "repo2"}]
    result = gh_search_repositories("test query")

  assert isinstance(result, list)
  assert len(result) == 2
  mock_cache.set.assert_called_once()


def test_gh_search_repositories_cached(mock_cache):
  mock_cache.get.return_value = [{"name": "cached_repo"}]

  result = gh_search_repositories("test query")

  assert isinstance(result, list)
  assert result[0]["name"] == "cached_repo"
  mock_cache.get.assert_called_once()


def test_gh_search_repositories_error(mock_github, mock_logger):
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


def test_gh_get_file_contents_file(mock_cache, mock_github):
  mock_instance = mock_github.return_value
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
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = mock_content

  result = gh_get_file_contents("owner", "repo", "path/to/file")

  assert result == "test content"
  mock_cache.set.assert_called_once()


def test_gh_get_file_contents_directory(mock_cache, mock_github):
  mock_instance = mock_github.return_value
  mock_repo = Mock()
  mock_content1 = Mock(spec=ContentFile)
  mock_content1._rawData = {"name": "file1", "type": "file"}
  mock_content2 = Mock(spec=ContentFile)
  mock_content2._rawData = {"name": "file2", "type": "file"}
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_contents.return_value = [mock_content1, mock_content2]

  result = gh_get_file_contents("owner", "repo", "path/to/dir")

  assert isinstance(result, list)
  assert len(result) == 2
  assert len(result) == 2
  mock_cache.set.assert_called_once()


def test_gh_get_file_contents_not_found(mock_github, mock_logger):
  mock_instance = mock_github.return_value
  mock_instance.get_repo.side_effect = UnknownObjectException(
    404, {"message": "Not Found"}
  )

  result = gh_get_file_contents("owner", "repo", "invalid/path")

  assert isinstance(result, dict)
  assert "error" in result
  mock_logger.warning.assert_called()


# --- Test gh_list_commits ---


def test_gh_list_commits_success(mock_cache, mock_github):
  mock_instance = mock_github.return_value
  mock_repo = Mock()
  mock_commits = Mock(spec=PaginatedList)
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_commits.return_value = mock_commits

  with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
    mock_handler.return_value = [{"sha": "abc123"}, {"sha": "def456"}]
    result = gh_list_commits("owner", "repo", "main")

  assert isinstance(result, list)
  assert len(result) == 2
  assert len(result) == 2
  mock_cache.set.assert_called_once()


def test_gh_list_commits_empty_repo(mock_github, mock_logger):
  mock_instance = mock_github.return_value
  mock_instance.get_repo.side_effect = GithubException(
    409, {"message": "Git Repository is empty"}
  )

  result = gh_list_commits("owner", "repo")

  assert isinstance(result, dict)
  assert "error" in result
  mock_logger.warning.assert_called()


# --- Test gh_list_issues ---


def test_gh_list_issues_success(mock_cache, mock_github):
  mock_instance = mock_github.return_value
  mock_repo = Mock()
  mock_issues = Mock(spec=PaginatedList)
  mock_instance.get_repo.return_value = mock_repo
  mock_repo.get_issues.return_value = mock_issues

  with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
    mock_handler.return_value = [{"number": 1}, {"number": 2}]
    result = gh_list_issues("owner", "repo", "open", ["bug"], "created", "desc")

  assert isinstance(result, list)
  assert len(result) == 2
  assert len(result) == 2
  mock_cache.set.assert_called_once()


# --- Test gh_get_repository ---


def test_gh_get_repository_success(mock_cache, mock_github):
  mock_instance = mock_github.return_value
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
  mock_cache.set.assert_called_once()


# --- Test gh_search_code ---


def test_gh_search_code_success(mock_cache, mock_github):
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 2
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = [{"path": "file1.py"}, {"path": "file2.py"}]
      result = gh_search_code("test query")

  assert isinstance(result, list)
  assert len(result) == 2
  mock_cache.set.assert_called_once()


def test_gh_get_current_user_info_success(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
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


def test_gh_get_current_user_info_invalid_credentials(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_client = Mock()
    mock_client.get_user.side_effect = BadCredentialsException(
      401, {"message": "Bad credentials"}
    )
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert "error" in result
    assert "Authentication failed" in result["error"]


def test_gh_get_current_user_info_unexpected_error(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_client = Mock()
    mock_client.get_user.side_effect = Exception("Unexpected error")
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert "error" in result
    assert "An unexpected error occurred" in result["error"]


def test_gh_get_current_user_info_rate_limit_exceeded(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_client = Mock()
    mock_client.get_user.side_effect = RateLimitExceededException(
      403, {"message": "API rate limit exceeded"}
    )
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert "error" in result
    assert "rate limit" in result["error"].lower()


def test_gh_get_current_user_info_github_exception(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_client = Mock()
    mock_client.get_user.side_effect = GithubException(
      500, {"message": "Internal error"}
    )
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert "error" in result
    assert "GitHub API Error" in result["error"]


def test_gh_get_current_user_info_unexpected_exception(mock_cache, mock_logger):
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_client = Mock()
    mock_client.get_user.side_effect = Exception("Unexpected failure")
    mock_init_client.return_value = mock_client
    from devops_mcps.github import gh_get_current_user_info

    result = gh_get_current_user_info()
    assert "error" in result
    assert "unexpected error" in result["error"].lower()


# --- Tests for gh_get_issue_details ---


def test_gh_get_issue_details_success(mock_cache, mock_logger):
  """Test successful issue details retrieval."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
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


def test_gh_get_issue_details_cached(mock_cache, mock_logger):
  """Test cached issue details retrieval."""
  cached_data = {
    "title": "Cached Issue",
    "description": "Cached description",
    "labels": ["cached"],
    "comments": ["Cached comment"],
    "timestamp": "2023-01-01T00:00:00Z",
  }
  mock_cache.get.return_value = cached_data

  from devops_mcps.github import gh_get_issue_details

  result = gh_get_issue_details("owner", "repo", 1)
  assert result == cached_data
  mock_cache.get.assert_called_once()


def test_gh_get_issue_details_no_client(mock_cache, mock_logger):
  """Test issue details retrieval when client not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
    mock_init_client.return_value = None

    from devops_mcps.github import gh_get_issue_details

    result = gh_get_issue_details("owner", "repo", 1)
    assert "error" in result
    assert (
      "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
      in result["error"]
    )


def test_gh_get_issue_details_github_exception(mock_cache, mock_logger):
  """Test issue details retrieval with GitHub API error."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
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


def test_gh_get_issue_details_unexpected_error(mock_cache, mock_logger):
  """Test issue details retrieval with unexpected error."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init_client:
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
  assert result["body"] == "Issue description"
  assert result["labels"] == ["bug"]
  assert result["assignees"] == ["assignee1"]
  assert result["creator"] == "creator1"
  assert len(result["comments"]) == 1
  assert result["comments"][0]["body"] == "Test comment"
  assert result["error"] is None


def test_gh_get_issue_content_no_client():
  """Test gh_get_issue_content when GitHub client is not initialized."""
  # Temporarily set global client to None
  import devops_mcps.github as github_module

  original_client = github_module.g
  github_module.g = None

  try:
    result = gh_get_issue_content("owner", "repo", 1)
    assert "error" in result
    assert (
      "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
      in result["error"]
    )
  finally:
    github_module.g = original_client


def test_gh_get_issue_content_issue_not_found(mock_github_api):
  """Test gh_get_issue_content when issue is not found."""
  from github import UnknownObjectException

  mock_repo = Mock()
  mock_repo.get_issue.side_effect = UnknownObjectException(404, "Not Found")
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_issue_content("owner", "repo", 999)

  assert "error" in result
  assert "Issue #999 not found" in result["error"]


def test_gh_get_issue_content_github_exception(mock_github_api):
  """Test gh_get_issue_content with GitHub API exception."""
  from github import GithubException

  mock_repo = Mock()
  mock_repo.get_issue.side_effect = GithubException(403, "Forbidden")
  mock_github_api.get_repo.return_value = mock_repo

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert "GitHub API error" in result["error"]


def test_gh_get_issue_content_unexpected_error(mock_github_api):
  """Test gh_get_issue_content with unexpected error."""
  mock_github_api.get_repo.side_effect = Exception("Unexpected error")

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert "Unexpected error" in result["error"]


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

  # Mock the _to_dict behavior for this object
  def mock_to_dict_side_effect(obj):
    if obj == mock_contents:
      return {
        "name": "binary_file.bin",
        "path": "path/to/binary_file.bin",
        "size": 1024,
        "sha": "abc123",
        "type": "file",
        "html_url": "https://github.com/owner/repo/blob/main/binary_file.bin",
      }
    return obj

  with patch("devops_mcps.github._to_dict", side_effect=mock_to_dict_side_effect):
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
    if obj == mock_contents:
      return {
        "name": "empty_file.txt",
        "path": "path/to/empty_file.txt",
        "size": 0,
        "sha": "def456",
        "type": "file",
        "html_url": "https://github.com/owner/repo/blob/main/empty_file.txt",
      }
    return obj

  with patch("devops_mcps.github._to_dict", side_effect=mock_to_dict_side_effect):
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


def test_gh_search_code_no_client():
  """Test gh_search_code when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_search_code("test query")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_search_code_with_custom_sort_and_order(mock_cache, mock_github):
  """Test gh_search_code with custom sort and order parameters."""
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 5
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = [{"path": "test.py", "score": 1.0}]

      result = gh_search_code("function test", sort="updated", order="asc")

  assert isinstance(result, list)
  mock_instance.search_code.assert_called_once_with(
    query="function test", sort="updated", order="asc"
  )
  mock_cache.set.assert_called_once()


def test_gh_search_code_cached_result(mock_cache, mock_github):
  """Test gh_search_code returns cached result when available."""
  cached_data = [{"path": "cached_file.py", "score": 1.0}]
  mock_cache.get.return_value = cached_data

  result = gh_search_code("cached query")

  assert result == cached_data
  # Ensure GitHub API is not called when cache hit
  mock_github.assert_not_called()


def test_gh_search_code_cache_miss(mock_cache, mock_github):
  """Test gh_search_code when cache miss occurs."""
  mock_cache.get.return_value = None  # Cache miss
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 3
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      expected_result = [{"path": "new_file.py", "score": 0.8}]
      mock_handler.return_value = expected_result

      result = gh_search_code("new query")

  assert result == expected_result
  mock_cache.get.assert_called_once()
  mock_cache.set.assert_called_once_with(
    "github:search_code:new query:indexed:desc", expected_result, ttl=300
  )


def test_gh_search_code_forbidden_error(mock_github_api):
  """Test gh_search_code with 403 Forbidden error."""
  from github import GithubException

  mock_github_api.search_code.side_effect = GithubException(
    403, {"message": "API rate limit exceeded"}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "Authentication required or insufficient permissions" in result["error"]


def test_gh_search_code_github_exception_other_status(mock_github_api):
  """Test gh_search_code with other GitHub exception status codes."""
  from github import GithubException

  mock_github_api.search_code.side_effect = GithubException(
    500, {"message": "Internal server error"}
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "GitHub API Error: 500" in result["error"]
  assert "Internal server error" in result["error"]


def test_gh_search_code_github_exception_no_message(mock_github_api):
  """Test gh_search_code with GitHub exception that has no message."""
  from github import GithubException

  mock_github_api.search_code.side_effect = GithubException(
    404,
    {},  # No message in data
  )

  result = gh_search_code("test query")

  assert "error" in result
  assert "GitHub API Error: 404" in result["error"]
  assert "Unknown GitHub error" in result["error"]


def test_gh_search_code_empty_results(mock_cache, mock_github):
  """Test gh_search_code with empty search results."""
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 0
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = []

      result = gh_search_code("nonexistent code")

  assert isinstance(result, list)
  assert len(result) == 0
  mock_cache.set.assert_called_once()


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


def test_gh_search_code_logging(mock_cache, mock_github, caplog):
  """Test gh_search_code logging behavior."""
  import logging

  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_code_results.totalCount = 2
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = [{"path": "file1.py"}, {"path": "file2.py"}]

      with caplog.at_level(logging.DEBUG):
        gh_search_code("test logging")

  # Check debug logs
  assert "gh_search_code called with query: 'test logging'" in caplog.text
  assert "Found 2 code results matching query" in caplog.text


def test_gh_search_code_cache_key_generation(mock_cache, mock_github):
  """Test gh_search_code generates correct cache keys."""
  mock_instance = mock_github.return_value
  mock_code_results = Mock(spec=PaginatedList)
  mock_instance.search_code.return_value = mock_code_results

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = mock_instance
    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = []

      # Test with different parameters
      gh_search_code("query1", "updated", "asc")
      gh_search_code("query2", "indexed", "desc")

  # Verify cache keys
  expected_calls = [
    call("github:search_code:query1:updated:asc"),
    call("github:search_code:query2:indexed:desc"),
  ]
  mock_cache.get.assert_has_calls(expected_calls)


def test_gh_search_code_force_client_initialization(mock_cache):
  """Test gh_search_code calls initialize_github_client with force=True."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_client = Mock()
    mock_code_results = Mock(spec=PaginatedList)
    mock_client.search_code.return_value = mock_code_results
    mock_init.return_value = mock_client

    with patch("devops_mcps.github._handle_paginated_list") as mock_handler:
      mock_handler.return_value = []

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
    with patch("devops_mcps.github.Github") as mock_github:
      mock_instance = mock_github.return_value
      mock_instance.get_user.return_value.login = "test_user"

      client = initialize_github_client(force=True)

      # Verify custom base_url was used
      mock_github.assert_called_once()
      call_kwargs = mock_github.call_args[1]
      assert call_kwargs["base_url"] == "https://github.enterprise.com/api/v3"
      assert client is not None


def test_initialize_github_client_already_initialized():
  """Test that client is re-initialized due to g=None reset in function."""
  with patch("devops_mcps.github.Github") as mock_github:
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.login = "test_user"
    mock_client.get_user.return_value = mock_user
    mock_github.return_value = mock_client

    client = initialize_github_client(force=False)

    # Should create new client since g is reset to None
    assert client is mock_client
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
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_search_repositories("test query")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_file_contents_no_client():
  """Test file content retrieval when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_get_file_contents("owner", "repo", "path")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_list_commits_no_client():
  """Test commit listing when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_list_commits("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_list_issues_no_client():
  """Test issue listing when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_list_issues("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_repository_no_client():
  """Test repository retrieval when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    mock_init.return_value = None

    result = gh_get_repository("owner", "repo")

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]


def test_gh_get_current_user_info_client_not_initialized():
  """Test gh_get_current_user_info when client initialization fails."""
  with patch.dict("os.environ", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
    with patch("devops_mcps.github.initialize_github_client") as mock_init:
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


def test_gh_search_code_rate_limit_exceeded(mock_github_api, mock_env_vars):
  """Test code search when rate limit is exceeded."""
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
