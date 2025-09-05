from unittest.mock import Mock, patch
from github import UnknownObjectException, GithubException
from devops_mcps.github import gh_get_issue_content


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_success(mock_init_client, mock_cache_patch):
  """Test successful retrieval of GitHub issue content."""
  mock_cache_patch.get.return_value = None  # No cached result

  mock_issue = Mock()
  mock_issue.title = "Test Issue"
  mock_issue.body = "Test Body"
  # Fix: Create proper mock labels with name attributes that can be accessed
  mock_bug = Mock()
  mock_bug.name = "bug"
  mock_feature = Mock()
  mock_feature.name = "feature"
  mock_issue.labels = [mock_bug, mock_feature]
  mock_issue.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
  mock_issue.updated_at.isoformat.return_value = "2024-01-02T00:00:00Z"
  mock_issue.assignees = [Mock(login="user1"), Mock(login="user2")]
  mock_issue.user.login = "creator"

  mock_comment = Mock()
  mock_comment.body = "Test Comment"
  mock_comment.user.login = "commenter"
  mock_comment.created_at.isoformat.return_value = "2024-01-03T00:00:00Z"
  mock_issue.get_comments.return_value = [mock_comment]

  mock_repo = Mock()
  mock_repo.get_issue.return_value = mock_issue

  mock_client = Mock()
  mock_client.get_repo.return_value = mock_repo
  mock_init_client.return_value = mock_client

  result = gh_get_issue_content("owner", "repo", 1)

  # Update assertions to match actual function return structure
  assert result["title"] == "Test Issue"
  assert (
    result["description"] == "Test Body"
  )  # Function returns 'description', not 'body'
  assert result["labels"] == ["bug", "feature"]
  assert (
    result["timestamp"] == "2024-01-01T00:00:00Z"
  )  # Function returns 'timestamp', not 'created_at'
  assert len(result["comments"]) == 1
  assert (
    result["comments"][0] == "Test Comment"
  )  # Function returns comment body strings, not objects


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_not_found(mock_init_client, mock_cache_patch):
  """Test handling of non-existent issue."""
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
def test_gh_get_issue_content_api_error(mock_init_client, mock_cache_patch):
  """Test handling of GitHub API errors."""
  mock_cache_patch.get.return_value = None  # No cached result

  mock_client = Mock()
  mock_repo = Mock()
  mock_repo.get_issue.side_effect = GithubException(
    500, {"message": "Internal Server Error"}
  )
  mock_client.get_repo.return_value = mock_repo
  mock_init_client.return_value = mock_client

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert "GitHub API Error: 500 - Internal Server Error" in result["error"]


@patch("devops_mcps.utils.github.github_issue_api.cache")
@patch("devops_mcps.utils.github.github_issue_api.initialize_github_client")
def test_gh_get_issue_content_no_client(mock_init_client, mock_cache_patch):
  """Test handling when GitHub client is not initialized."""
  mock_cache_patch.get.return_value = None  # No cached result
  mock_init_client.return_value = None  # No client initialized

  result = gh_get_issue_content("owner", "repo", 1)

  assert "error" in result
  assert (
    result["error"]
    == "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
  )
