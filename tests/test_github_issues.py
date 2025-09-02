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

  with patch("devops_mcps.github.github_issues.get_github_client") as mock_get_client:
    mock_github = Mock()
    mock_get_client.return_value = mock_github
    mock_github.get_repo.return_value = mock_repo

    result = gh_get_issue_content("owner", "repo", 1)

    assert "error" not in result
    assert result["issue"]["title"] == "Test Issue"
    assert result["issue"]["body"] == "Test Body"
    assert len(result["issue"]["labels"]) == 2
    assert result["issue"]["created_at"] == "2024-01-01T00:00:00Z"
    assert result["issue"]["updated_at"] == "2024-01-02T00:00:00Z"
    assert len(result["issue"]["assignees"]) == 2
    assert len(result["comments"]) == 1
    assert result["comments"][0]["body"] == "Test Comment"
    assert result["comments"][0]["created_at"] == "2024-01-03T00:00:00Z"


def test_gh_get_issue_content_not_found():
  """Test handling when issue is not found."""
  from devops_mcps.github.cache import cache_manager
  
  # Clear cache to ensure fresh test
  cache_manager.clear()
  
  with patch("devops_mcps.github.github_issues.get_github_client") as mock_get_client:
    mock_github = Mock()
    mock_get_client.return_value = mock_github
    mock_repo = Mock()
    mock_github.get_repo.return_value = mock_repo
    mock_repo.get_issue.side_effect = UnknownObjectException(404, "Not Found")
    
    result = gh_get_issue_content("owner", "repo", 1)

    assert "error" in result
    assert "Issue #1 not found" in result["error"]
    assert "issue" not in result
    assert "comments" not in result


def test_gh_get_issue_content_api_error():
  """Test handling of GitHub API errors."""
  from devops_mcps.cache import cache_manager
  
  # Clear cache to ensure fresh test
  cache_manager.clear()
  
  with patch("devops_mcps.github.github_issues.get_github_client") as mock_get_client:
    mock_client = Mock()
    mock_repo = Mock()
    
    mock_get_client.return_value = mock_client
    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_issue.side_effect = GithubException(404, "Not Found")
    
    result = gh_get_issue_content("owner", "repo", 1)

    assert "error" in result
    assert "GitHub API error" in result["error"]
    assert "issue" not in result
    assert "comments" not in result


def test_gh_get_issue_content_no_client():
  """Test handling when GitHub client is not initialized."""
  from devops_mcps.cache import cache_manager
  
  # Reset global client state to ensure clean test environment
  from devops_mcps.github.github_client import reset_github_client
  reset_github_client()
  
  # Clear cache to ensure fresh test
  cache_manager.clear()
  
  with patch("devops_mcps.github.github_issues.get_github_client") as mock_get_client:
    mock_get_client.side_effect = ValueError("GitHub client not initialized")
    
    result = gh_get_issue_content("owner", "repo", 1)

    assert "error" in result
    assert "GitHub client not initialized" in result["error"]
    assert "issue" not in result
    assert "comments" not in result
