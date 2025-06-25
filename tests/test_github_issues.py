from unittest.mock import Mock, patch
from github import UnknownObjectException, GithubException
from devops_mcps.github import gh_get_issue_content


def test_gh_get_issue_content_success():
  """Test successful retrieval of GitHub issue content."""
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

  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    with patch("devops_mcps.github.g") as mock_github:
      mock_init.return_value = mock_github
      mock_github.get_repo.return_value = mock_repo

      result = gh_get_issue_content("owner", "repo", 1)

      assert result["title"] == "Test Issue"
      assert result["body"] == "Test Body"
      assert result["labels"] == ["bug", "feature"]
      assert result["created_at"] == "2024-01-01T00:00:00Z"
      assert result["updated_at"] == "2024-01-02T00:00:00Z"
      assert result["assignees"] == ["user1", "user2"]
      assert result["creator"] == "creator"
      assert result["error"] is None
      assert len(result["comments"]) == 1
      assert result["comments"][0]["body"] == "Test Comment"
      assert result["comments"][0]["user"] == "commenter"
      assert result["comments"][0]["created_at"] == "2024-01-03T00:00:00Z"


def test_gh_get_issue_content_not_found():
  """Test handling of non-existent issue."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    with patch("devops_mcps.github.g") as mock_github:
      mock_init.return_value = mock_github
      mock_github.get_repo.side_effect = UnknownObjectException(
        status=404, data={"message": "Not Found"}
      )

      result = gh_get_issue_content("owner", "repo", 999)

      assert result["error"] == "Issue #999 not found in owner/repo"
      assert result["title"] is None
      assert result["body"] is None
      assert result["labels"] is None
      assert result["created_at"] is None
      assert result["updated_at"] is None
      assert result["comments"] is None
      assert result["assignees"] is None
      assert result["creator"] is None


def test_gh_get_issue_content_api_error():
  """Test handling of GitHub API errors."""
  with patch("devops_mcps.github.initialize_github_client") as mock_init:
    with patch("devops_mcps.github.g") as mock_github:
      mock_init.return_value = mock_github
      mock_github.get_repo.side_effect = GithubException(
        status=500, data={"message": "Internal Server Error"}
      )

      result = gh_get_issue_content("owner", "repo", 1)

      assert "GitHub API error" in result["error"]
      assert result["title"] is None
      assert result["body"] is None
      assert result["labels"] is None
      assert result["created_at"] is None
      assert result["updated_at"] is None
      assert result["comments"] is None
      assert result["assignees"] is None
      assert result["creator"] is None


def test_gh_get_issue_content_no_client():
  """Test handling when GitHub client is not initialized."""
  with patch("devops_mcps.github.initialize_github_client", return_value=None):
    with patch("devops_mcps.github.g", None):  # Fix: Ensure g is None
      result = gh_get_issue_content("owner", "repo", 1)

      assert (
        result["error"]
        == "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
      )
      assert result["title"] is None
      assert result["body"] is None
      assert result["labels"] is None
      assert result["created_at"] is None
      assert result["updated_at"] is None
      assert result["comments"] is None
      assert result["assignees"] is None
      assert result["creator"] is None
