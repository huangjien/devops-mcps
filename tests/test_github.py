import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch

from devops_mcps.github import (
  initialize_github_client,
  _to_dict,
  _handle_paginated_list,
  gh_search_repositories,
  gh_get_file_contents,
  gh_list_commits,
  gh_list_issues,
  gh_get_repository,
  gh_search_code,  # Add this import
)
from github import (
  UnknownObjectException,
  BadCredentialsException,
  RateLimitExceededException,  # Add this import
  GithubException,  # Add this import
)
from github.Repository import Repository
from github.Commit import Commit
from github.Issue import Issue
from github.ContentFile import ContentFile
from github.PaginatedList import PaginatedList

# --- Test Fixtures ---


@pytest.fixture
def mock_github():
  with patch("devops_mcps.github.Github") as mock:
    yield mock


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
    "test_token", timeout=60, per_page=10, base_url="https://api.github.com"
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
  assert client is not None
  mock_github.assert_called_once_with(
    timeout=60, per_page=10, base_url="https://api.github.com"
  )
  mock_logger.warning.assert_called_once()
  mock_logger.info.assert_called_once()
  mock_logger.warning.assert_called()
  mock_logger.info.assert_called()


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
  mock_issue = Mock(spec=Issue)
  mock_issue.number = 1
  mock_issue.title = "Test issue"
  mock_issue.state = "open"
  mock_issue.html_url = "https://github.com/owner/repo/issues/1"
  mock_issue.user = Mock()
  mock_issue.user.login = "user1"

  label1 = Mock()
  label1.name = "bug"
  label2 = Mock()
  label2.name = "enhancement"
  mock_issue.labels = [label1, label2]

  assignee1 = Mock()
  assignee1.login = "user2"
  assignee2 = Mock()
  assignee2.login = "user3"
  mock_issue.assignees = [assignee1, assignee2]
  mock_issue.assignee = None
  mock_issue.pull_request = None

  result = _to_dict(mock_issue)

  assert isinstance(result, dict)
  assert result["number"] == 1
  assert result["title"] == "Test issue"
  assert sorted(result["label_names"]) == sorted(["bug", "enhancement"])
  assert sorted(result["assignee_logins"]) == sorted(["user2", "user3"])
  assert result["is_pull_request"] is False


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
  mock_instance.search_code.return_value = mock_code_results

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
