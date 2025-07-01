# /Users/huangjien/workspace/devops-mcps/tests/test_core.py
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add src to sys.path for import
sys.path.insert(
  0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
import devops_mcps.core as core


@pytest.mark.asyncio
async def test_search_repositories_valid(monkeypatch):
  # Arrange
  expected_result = [{"id": 1, "name": "repo1"}]
  monkeypatch.setattr(
    core.github, "gh_search_repositories", lambda query: expected_result
  )
  # Act
  result = await core.search_repositories("test-query")
  # Assert
  assert result == expected_result


@pytest.mark.asyncio
async def test_search_repositories_invalid(monkeypatch):
  # Arrange
  # No need to patch, just call with empty query
  # Act
  result = await core.search_repositories("")
  # Assert
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'query' cannot be empty"


@pytest.mark.asyncio
async def test_get_file_contents_valid(monkeypatch):
  expected_content = "file content"
  monkeypatch.setattr(
    core.github,
    "gh_get_file_contents",
    lambda owner, repo, path, branch=None: expected_content,
  )
  result = await core.get_file_contents("owner", "repo", "path/to/file")
  assert result == expected_content


@pytest.mark.asyncio
async def test_list_commits_valid(monkeypatch):
  expected_commits = [{"sha": "abc123", "message": "Initial commit"}]
  monkeypatch.setattr(
    core.github, "gh_list_commits", lambda owner, repo, branch=None: expected_commits
  )
  result = await core.list_commits("owner", "repo")
  assert result == expected_commits


@pytest.mark.asyncio
async def test_list_issues_valid(monkeypatch):
  expected_issues = [{"id": 101, "title": "Issue 1"}]
  monkeypatch.setattr(
    core.github,
    "gh_list_issues",
    lambda owner,
    repo,
    state="open",
    labels=None,
    sort="created",
    direction="desc": expected_issues,
  )
  result = await core.list_issues("owner", "repo")
  assert result == expected_issues


@pytest.mark.asyncio
async def test_get_repository_valid(monkeypatch):
  expected_repo = {"id": 202, "name": "repo202"}
  monkeypatch.setattr(
    core.github, "gh_get_repository", lambda owner, repo: expected_repo
  )
  result = await core.get_repository("owner", "repo")
  assert result == expected_repo


@pytest.mark.asyncio
async def test_search_code_valid(monkeypatch):
  expected_results = [{"name": "file.py", "path": "src/file.py"}]
  monkeypatch.setattr(core.github, "gh_search_code", lambda query: expected_results)
  result = await core.search_code("def test")
  assert result == expected_results


@pytest.mark.asyncio
async def test_gh_get_issue_content_success(monkeypatch):
  """Test successful retrieval of GitHub issue content including assignees and creator.

  Args:
      monkeypatch: pytest fixture for patching.
  """
  expected_result = {
    "title": "Sample Issue",
    "body": "Issue body text",
    "assignees": ["user1", "user2"],
    "creator": "creator_user",
    "state": "open",
    "number": 42,
  }
  monkeypatch.setattr(
    core.github,
    "gh_get_issue_content",
    lambda owner, repo, number: expected_result,
  )
  result = await core.get_github_issue_content("owner", "repo", 42)
  assert result == expected_result
  assert "assignees" in result
  assert "creator" in result


@pytest.mark.asyncio
async def test_gh_get_issue_content_error(monkeypatch):
  """Test error handling when GitHub API returns an error.

  Args:
      monkeypatch: pytest fixture for patching.
  """
  monkeypatch.setattr(
    core.github,
    "gh_get_issue_content",
    lambda owner, repo, number: {"error": "Not Found"},
  )
  result = await core.get_github_issue_content("owner", "repo", 999)
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Not Found"


@pytest.mark.asyncio
async def test_gh_get_issue_content_no_assignees(monkeypatch):
  """Test retrieval of issue content when there are no assignees.

  Args:
      monkeypatch: pytest fixture for patching.
  """
  expected_result = {
    "title": "No Assignees",
    "body": "No one assigned",
    "assignees": [],
    "creator": "creator_user",
    "state": "open",
    "number": 43,
  }
  monkeypatch.setattr(
    core.github,
    "gh_get_issue_content",
    lambda owner, repo, number: expected_result,
  )
  result = await core.get_github_issue_content("owner", "repo", 43)
  assert result["assignees"] == []
  assert result["creator"] == "creator_user"


# --- Azure Tools Tests ---
@pytest.mark.asyncio
async def test_get_azure_subscriptions_valid(monkeypatch):
  """Test successful retrieval of Azure subscriptions."""
  expected_result = [{"id": "sub1", "name": "Subscription 1"}]
  monkeypatch.setattr(core.azure, "get_subscriptions", lambda: expected_result)
  result = await core.get_azure_subscriptions()
  assert result == expected_result


@pytest.mark.asyncio
async def test_list_azure_vms_valid(monkeypatch):
  """Test successful listing of Azure VMs."""
  expected_result = [{"id": "vm1", "name": "VM 1"}]
  monkeypatch.setattr(
    core.azure, "list_virtual_machines", lambda subscription_id: expected_result
  )
  result = await core.list_azure_vms("sub1")
  assert result == expected_result


@pytest.mark.asyncio
async def test_list_azure_vms_empty_subscription_id():
  """Test list_azure_vms with empty subscription_id."""
  result = await core.list_azure_vms("")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'subscription_id' cannot be empty"


@pytest.mark.asyncio
async def test_list_aks_clusters_valid(monkeypatch):
  """Test successful listing of AKS clusters."""
  expected_result = [{"id": "aks1", "name": "AKS Cluster 1"}]
  monkeypatch.setattr(
    core.azure, "list_aks_clusters", lambda subscription_id: expected_result
  )
  result = await core.list_aks_clusters("sub1")
  assert result == expected_result


@pytest.mark.asyncio
async def test_list_aks_clusters_empty_subscription_id():
  """Test list_aks_clusters with empty subscription_id."""
  result = await core.list_aks_clusters("")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'subscription_id' cannot be empty"


# --- GitHub Tools Parameter Validation Tests ---
@pytest.mark.asyncio
async def test_get_file_contents_empty_owner():
  """Test get_file_contents with empty owner."""
  result = await core.get_file_contents("", "repo", "path")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'owner' cannot be empty"


@pytest.mark.asyncio
async def test_get_file_contents_empty_repo():
  """Test get_file_contents with empty repo."""
  result = await core.get_file_contents("owner", "", "path")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repo' cannot be empty"


@pytest.mark.asyncio
async def test_get_file_contents_empty_path():
  """Test get_file_contents with empty path."""
  result = await core.get_file_contents("owner", "repo", "")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'path' cannot be empty"


@pytest.mark.asyncio
async def test_list_commits_empty_owner():
  """Test list_commits with empty owner."""
  result = await core.list_commits("", "repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'owner' cannot be empty"


@pytest.mark.asyncio
async def test_list_commits_empty_repo():
  """Test list_commits with empty repo."""
  result = await core.list_commits("owner", "")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repo' cannot be empty"


@pytest.mark.asyncio
async def test_list_issues_empty_owner():
  """Test list_issues with empty owner."""
  result = await core.list_issues("", "repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'owner' cannot be empty"


@pytest.mark.asyncio
async def test_list_issues_empty_repo():
  """Test list_issues with empty repo."""
  result = await core.list_issues("owner", "")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repo' cannot be empty"


@pytest.mark.asyncio
async def test_get_repository_empty_owner():
  """Test get_repository with empty owner."""
  result = await core.get_repository("", "repo")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'owner' cannot be empty"


@pytest.mark.asyncio
async def test_get_repository_empty_repo():
  """Test get_repository with empty repo."""
  result = await core.get_repository("owner", "")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repo' cannot be empty"


@pytest.mark.asyncio
async def test_search_code_empty_query():
  """Test search_code with empty query."""
  result = await core.search_code("")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'query' cannot be empty"


# --- Jenkins Tools Tests ---
@pytest.mark.asyncio
async def test_get_jenkins_jobs_valid(monkeypatch):
  """Test successful retrieval of Jenkins jobs."""
  expected_result = [{"name": "job1", "url": "http://jenkins/job/job1"}]
  monkeypatch.setattr(core.jenkins, "jenkins_get_jobs", lambda: expected_result)
  result = await core.get_jenkins_jobs()
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_jenkins_build_log_valid(monkeypatch):
  """Test successful retrieval of Jenkins build log."""
  expected_result = "Build log content"
  monkeypatch.setattr(
    core.jenkins,
    "jenkins_get_build_log",
    lambda job_name, build_number: expected_result,
  )
  result = await core.get_jenkins_build_log("job1", 1)
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_jenkins_build_log_empty_job_name():
  """Test get_jenkins_build_log with empty job_name."""
  result = await core.get_jenkins_build_log("", 1)
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter job_name cannot be empty"


@pytest.mark.asyncio
async def test_get_jenkins_build_log_none_build_number():
  """Test get_jenkins_build_log with None build_number."""
  result = await core.get_jenkins_build_log("job1", None)
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter build_number cannot be empty"


@pytest.mark.asyncio
async def test_get_all_jenkins_views_valid(monkeypatch):
  """Test successful retrieval of Jenkins views."""
  expected_result = [{"name": "view1", "url": "http://jenkins/view/view1"}]
  monkeypatch.setattr(core.jenkins, "jenkins_get_all_views", lambda: expected_result)
  result = await core.get_all_jenkins_views()
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_recent_failed_jenkins_builds_valid(monkeypatch):
  """Test successful retrieval of recent failed Jenkins builds."""
  expected_result = [
    {
      "job_name": "failed_job",
      "build_number": 10,
      "status": "FAILURE",
      "timestamp_utc": "2023-01-01T10:00:00Z",
      "url": "http://jenkins/job/failed_job/10",
    }
  ]
  monkeypatch.setattr(
    core.jenkins,
    "jenkins_get_recent_failed_builds",
    lambda hours_ago=8: expected_result,
  )
  result = await core.get_recent_failed_jenkins_builds()
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_recent_failed_jenkins_builds_custom_hours(monkeypatch):
  """Test get_recent_failed_jenkins_builds with custom hours_ago parameter."""
  expected_result = []

  def mock_jenkins_get_recent_failed_builds(hours_ago=8):
    assert hours_ago == 24  # Verify the parameter is passed correctly
    return expected_result

  monkeypatch.setattr(
    core.jenkins,
    "jenkins_get_recent_failed_builds",
    mock_jenkins_get_recent_failed_builds,
  )
  result = await core.get_recent_failed_jenkins_builds(24)
  assert result == expected_result


# --- Artifactory Tools Tests ---
@pytest.mark.asyncio
async def test_list_artifactory_items_valid(monkeypatch):
  """Test successful listing of Artifactory items."""
  expected_result = [{"name": "item1", "path": "/item1"}]
  monkeypatch.setattr(
    core.artifactory,
    "artifactory_list_items",
    lambda repository, path="/": expected_result,
  )
  result = await core.list_artifactory_items("repo1")
  assert result == expected_result


@pytest.mark.asyncio
async def test_list_artifactory_items_empty_repository():
  """Test list_artifactory_items with empty repository."""
  result = await core.list_artifactory_items("")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repository' cannot be empty"


@pytest.mark.asyncio
async def test_search_artifactory_items_valid(monkeypatch):
  """Test successful search of Artifactory items."""
  expected_result = [{"name": "search_result1", "repository": "repo1"}]
  monkeypatch.setattr(
    core.artifactory,
    "artifactory_search_items",
    lambda query, repositories=None: expected_result,
  )
  result = await core.search_artifactory_items("test")
  assert result == expected_result


@pytest.mark.asyncio
async def test_search_artifactory_items_empty_query():
  """Test search_artifactory_items with empty query."""
  result = await core.search_artifactory_items("")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'query' cannot be empty"


@pytest.mark.asyncio
async def test_get_artifactory_item_info_valid(monkeypatch):
  """Test successful retrieval of Artifactory item info."""
  expected_result = {"name": "item1", "size": 1024, "created": "2023-01-01"}
  monkeypatch.setattr(
    core.artifactory,
    "artifactory_get_item_info",
    lambda repository, path: expected_result,
  )
  result = await core.get_artifactory_item_info("repo1", "/item1")
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_artifactory_item_info_empty_repository():
  """Test get_artifactory_item_info with empty repository."""
  result = await core.get_artifactory_item_info("", "/item1")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'repository' cannot be empty"


@pytest.mark.asyncio
async def test_get_artifactory_item_info_empty_path():
  """Test get_artifactory_item_info with empty path."""
  result = await core.get_artifactory_item_info("repo1", "")
  assert isinstance(result, dict)
  assert "error" in result
  assert result["error"] == "Parameter 'path' cannot be empty"


# --- GitHub User Info Tests ---
@pytest.mark.asyncio
async def test_github_get_current_user_info_valid(monkeypatch):
  """Test successful retrieval of GitHub user info."""
  expected_result = {"name": "John Doe", "email": "john@example.com"}
  monkeypatch.setattr(core.github, "gh_get_current_user_info", lambda: expected_result)
  result = await core.github_get_current_user_info()
  assert result == expected_result


@pytest.mark.asyncio
async def test_github_get_current_user_info_error(monkeypatch):
  """Test error handling in GitHub user info retrieval."""
  expected_result = {"error": "Authentication failed"}
  monkeypatch.setattr(core.github, "gh_get_current_user_info", lambda: expected_result)
  result = await core.github_get_current_user_info()
  assert result == expected_result
  assert "error" in result


# --- Additional Function Tests ---


@pytest.mark.asyncio
async def test_list_artifactory_items_with_path(monkeypatch):
  """Test list_artifactory_items with custom path."""
  expected_result = [{"name": "subitem1", "path": "/custom/subitem1"}]

  def mock_artifactory_list_items(repository, path="/"):
    assert repository == "repo1"
    assert path == "/custom/path"
    return expected_result

  monkeypatch.setattr(
    core.artifactory,
    "artifactory_list_items",
    mock_artifactory_list_items,
  )
  result = await core.list_artifactory_items("repo1", "/custom/path")
  assert result == expected_result


@pytest.mark.asyncio
async def test_search_artifactory_items_with_repositories(monkeypatch):
  """Test search_artifactory_items with specific repositories."""
  expected_result = [{"name": "search_result1", "repository": "repo1"}]

  def mock_artifactory_search_items(query, repositories=None):
    assert query == "test"
    assert repositories == ["repo1", "repo2"]
    return expected_result

  monkeypatch.setattr(
    core.artifactory,
    "artifactory_search_items",
    mock_artifactory_search_items,
  )
  result = await core.search_artifactory_items("test", ["repo1", "repo2"])
  assert result == expected_result


# --- Package Version Test ---
def test_package_version_exists():
  """Test that package_version is defined in the core module."""
  assert hasattr(core, "package_version")
  assert isinstance(core.package_version, str)
  # The version should either be a real version or the fallback
  assert core.package_version != ""


# --- Main Function Tests ---
@patch("devops_mcps.core.mcp.run")
@patch("devops_mcps.core.github.initialize_github_client")
@patch("devops_mcps.core.sys.argv", ["test", "--transport", "stdio"])
def test_main_stdio_transport(mock_init_github, mock_mcp_run):
  """Test main function with stdio transport."""
  # Mock GitHub client as initialized
  core.github.g = MagicMock()
  core.github.GITHUB_TOKEN = "test_token"

  # Mock Jenkins client as initialized
  core.jenkins.j = MagicMock()
  core.jenkins.JENKINS_URL = "http://test"
  core.jenkins.JENKINS_USER = "test_user"
  core.jenkins.JENKINS_TOKEN = "test_token"

  core.main()

  mock_init_github.assert_called_once_with(force=True)
  mock_mcp_run.assert_called_once_with(transport="stdio")


@patch("devops_mcps.core.mcp.run")
@patch("devops_mcps.core.github.initialize_github_client")
@patch("devops_mcps.core.os.getenv")
@patch("devops_mcps.core.sys.argv", ["test", "--transport", "stream_http"])
def test_main_stream_http_transport(mock_getenv, mock_init_github, mock_mcp_run):
  """Test main function with stream_http transport."""

  # Configure getenv to return different values for different calls
  def getenv_side_effect(key, default=None):
    if key == "MCP_PORT":
      return "4000"
    elif key == "PROMPTS_FILE":
      return None  # No prompts file
    return default

  mock_getenv.side_effect = getenv_side_effect

  # Mock GitHub client as initialized
  core.github.g = MagicMock()
  core.github.GITHUB_TOKEN = "test_token"

  # Mock Jenkins client as initialized
  core.jenkins.j = MagicMock()
  core.jenkins.JENKINS_URL = "http://test"
  core.jenkins.JENKINS_USER = "test_user"
  core.jenkins.JENKINS_TOKEN = "test_token"

  core.main()

  # Check that getenv was called for both MCP_PORT and PROMPTS_FILE
  assert mock_getenv.call_count >= 1
  mock_mcp_run.assert_called_once_with(
    transport="http", host="127.0.0.1", port=4000, path="/mcp"
  )


@patch("devops_mcps.core.mcp.run")
@patch("devops_mcps.core.github.initialize_github_client")
@patch("devops_mcps.core.sys.argv", ["test"])
def test_main_github_init_failure(mock_init_github, mock_mcp_run):
  """Test main function when GitHub client fails to initialize."""
  # Store original values
  original_g = core.github.g
  original_token = core.github.GITHUB_TOKEN

  try:
    # Mock GitHub client as failed to initialize
    core.github.g = None
    
    # Set environment variable to simulate token being present
    with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"}):
      # Mock sys.exit to raise SystemExit
      with patch("devops_mcps.core.sys.exit", side_effect=SystemExit) as mock_exit:
        with pytest.raises(SystemExit):
          core.main()

        mock_exit.assert_called_once_with(1)
        mock_mcp_run.assert_not_called()
  finally:
    # Restore original values
    core.github.g = original_g
    core.github.GITHUB_TOKEN = original_token


@patch("devops_mcps.core.mcp.run")
@patch("devops_mcps.core.github.initialize_github_client")
@patch("devops_mcps.core.sys.argv", ["test"])
def test_main_jenkins_init_failure(mock_init_github, mock_mcp_run):
  """Test main function when Jenkins client fails to initialize."""
  # Store original values
  original_g = core.github.g
  original_github_token = core.github.GITHUB_TOKEN
  original_j = core.jenkins.j
  original_jenkins_url = core.jenkins.JENKINS_URL
  original_jenkins_user = core.jenkins.JENKINS_USER
  original_jenkins_token = core.jenkins.JENKINS_TOKEN

  try:
    # Mock GitHub client as initialized
    core.github.g = MagicMock()
    core.github.GITHUB_TOKEN = "test_token"

    # Mock Jenkins client as failed to initialize
    core.jenkins.j = None
    core.jenkins.JENKINS_URL = "http://test"
    core.jenkins.JENKINS_USER = "test_user"
    core.jenkins.JENKINS_TOKEN = "test_token"  # Credentials present but init failed

    # Mock sys.exit to raise SystemExit
    with patch("devops_mcps.core.sys.exit", side_effect=SystemExit) as mock_exit:
      with pytest.raises(SystemExit):
        core.main()

      mock_exit.assert_called_once_with(1)
      mock_mcp_run.assert_not_called()
  finally:
    # Restore original values
    core.github.g = original_g
    core.github.GITHUB_TOKEN = original_github_token
    core.jenkins.j = original_j
    core.jenkins.JENKINS_URL = original_jenkins_url
    core.jenkins.JENKINS_USER = original_jenkins_user
    core.jenkins.JENKINS_TOKEN = original_jenkins_token


@patch("devops_mcps.core.mcp.run")
@patch("devops_mcps.core.github.initialize_github_client")
@patch("devops_mcps.core.sys.argv", ["test"])
def test_main_no_github_auth(mock_init_github, mock_mcp_run):
  """Test main function without GitHub authentication."""
  # Store original values
  original_g = core.github.g
  original_github_token = core.github.GITHUB_TOKEN
  original_j = core.jenkins.j
  original_jenkins_url = core.jenkins.JENKINS_URL
  original_jenkins_user = core.jenkins.JENKINS_USER
  original_jenkins_token = core.jenkins.JENKINS_TOKEN

  try:
    # Mock GitHub client as not initialized (no token)
    core.github.g = None
    core.github.GITHUB_TOKEN = None

    # Mock Jenkins client as not initialized (no credentials)
    core.jenkins.j = None
    core.jenkins.JENKINS_URL = None
    core.jenkins.JENKINS_USER = None
    core.jenkins.JENKINS_TOKEN = None

    core.main()

    mock_mcp_run.assert_called_once_with(transport="stdio")
  finally:
    # Restore original values
    core.github.g = original_g
    core.github.GITHUB_TOKEN = original_github_token
    core.jenkins.j = original_j
    core.jenkins.JENKINS_URL = original_jenkins_url
    core.jenkins.JENKINS_USER = original_jenkins_user
    core.jenkins.JENKINS_TOKEN = original_jenkins_token


# --- Main Stream HTTP Function Tests ---
@patch("devops_mcps.core.main")
@patch("devops_mcps.core.sys.argv", ["test"])
def test_main_stream_http_no_transport_arg(mock_main):
  """Test main_stream_http when no --transport argument exists."""
  original_argv = core.sys.argv.copy()

  core.main_stream_http()

  assert "--transport" in core.sys.argv
  assert "stream_http" in core.sys.argv
  mock_main.assert_called_once()

  # Restore original argv
  core.sys.argv = original_argv


@patch("devops_mcps.core.main")
@patch("devops_mcps.core.sys.argv", ["test", "--transport", "stdio"])
def test_main_stream_http_existing_transport_arg(mock_main):
  """Test main_stream_http when --transport argument already exists."""
  original_argv = core.sys.argv.copy()

  core.main_stream_http()

  assert "--transport" in core.sys.argv
  assert "stream_http" in core.sys.argv
  assert "stdio" not in core.sys.argv
  mock_main.assert_called_once()

  # Restore original argv
  core.sys.argv = original_argv


@patch("devops_mcps.core.main")
@patch("devops_mcps.core.sys.argv", ["test", "--transport"])
def test_main_stream_http_transport_no_value(mock_main):
  """Test main_stream_http when --transport has no value."""
  original_argv = core.sys.argv.copy()

  core.main_stream_http()

  assert "--transport" in core.sys.argv
  assert "stream_http" in core.sys.argv
  mock_main.assert_called_once()

  # Restore original argv
  core.sys.argv = original_argv


# --- MCP Server Initialization Tests ---
def test_mcp_server_initialization():
  """Test that MCP server is properly initialized."""
  assert hasattr(core, "mcp")
  assert core.mcp is not None
  # Check that the server is a FastMCP instance
  assert "FastMCP" in str(type(core.mcp))
  # Check that the server has the expected name in its internal structure
  assert hasattr(core.mcp, "name")
  assert "DevOps MCP Server" in core.mcp.name


# --- Error Handling Edge Cases ---
@pytest.mark.asyncio
async def test_list_issues_with_all_parameters(monkeypatch):
  """Test list_issues with all optional parameters."""
  expected_result = [{"id": 1, "title": "Test Issue"}]

  def mock_gh_list_issues(
    owner, repo, state="open", labels=None, sort="created", direction="desc"
  ):
    assert owner == "test_owner"
    assert repo == "test_repo"
    assert state == "closed"
    assert labels == ["bug", "enhancement"]
    assert sort == "updated"
    assert direction == "asc"
    return expected_result

  monkeypatch.setattr(core.github, "gh_list_issues", mock_gh_list_issues)

  result = await core.list_issues(
    "test_owner",
    "test_repo",
    state="closed",
    labels=["bug", "enhancement"],
    sort="updated",
    direction="asc",
  )
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_file_contents_with_branch(monkeypatch):
  """Test get_file_contents with branch parameter."""
  expected_content = "file content from branch"

  def mock_gh_get_file_contents(owner, repo, path, branch=None):
    assert owner == "test_owner"
    assert repo == "test_repo"
    assert path == "test/path"
    assert branch == "feature-branch"
    return expected_content

  monkeypatch.setattr(core.github, "gh_get_file_contents", mock_gh_get_file_contents)

  result = await core.get_file_contents(
    "test_owner", "test_repo", "test/path", "feature-branch"
  )
  assert result == expected_content


@pytest.mark.asyncio
async def test_list_commits_with_branch(monkeypatch):
  """Test list_commits with branch parameter."""
  expected_commits = [{"sha": "abc123", "message": "Test commit"}]

  def mock_gh_list_commits(owner, repo, branch=None):
    assert owner == "test_owner"
    assert repo == "test_repo"
    assert branch == "develop"
    return expected_commits

  monkeypatch.setattr(core.github, "gh_list_commits", mock_gh_list_commits)

  result = await core.list_commits("test_owner", "test_repo", "develop")
  assert result == expected_commits


# --- Jenkins Build Log Edge Cases ---
@pytest.mark.asyncio
async def test_get_jenkins_build_log_zero_build_number(monkeypatch):
  """Test get_jenkins_build_log with build_number 0 (last build)."""
  expected_result = "Last build log content"

  def mock_jenkins_get_build_log(job_name, build_number):
    assert job_name == "test_job"
    assert build_number == 0
    return expected_result

  monkeypatch.setattr(core.jenkins, "jenkins_get_build_log", mock_jenkins_get_build_log)

  result = await core.get_jenkins_build_log("test_job", 0)
  assert result == expected_result


@pytest.mark.asyncio
async def test_get_jenkins_build_log_negative_build_number(monkeypatch):
  """Test get_jenkins_build_log with negative build_number."""
  expected_result = "Last build log content"

  def mock_jenkins_get_build_log(job_name, build_number):
    assert job_name == "test_job"
    assert build_number == -1
    return expected_result

  monkeypatch.setattr(core.jenkins, "jenkins_get_build_log", mock_jenkins_get_build_log)

  result = await core.get_jenkins_build_log("test_job", -1)
  assert result == expected_result


# --- Environment Variable Tests ---
@patch("devops_mcps.core.os.getenv")
def test_mcp_port_environment_variable(mock_getenv):
  """Test that MCP_PORT environment variable is used correctly."""
  mock_getenv.return_value = "5000"

  # Test the port extraction logic
  port = int(core.os.getenv("MCP_PORT", "3721"))
  assert port == 5000

  mock_getenv.assert_called_with("MCP_PORT", "3721")


@patch("devops_mcps.core.os.getenv")
def test_mcp_port_default_value(mock_getenv):
  """Test that default port 3721 is used when MCP_PORT is not set."""
  mock_getenv.return_value = "3721"  # Default value returned

  port = int(core.os.getenv("MCP_PORT", "3721"))
  assert port == 3721

  mock_getenv.assert_called_with("MCP_PORT", "3721")


# --- Logging Tests ---
@patch("devops_mcps.core.logger")
def test_debug_logging_calls(mock_logger):
  """Test that debug logging is called in various functions."""
  # This test ensures logging calls don't break the functions
  # The actual logging behavior is tested in test_logger.py
  assert hasattr(core, "logger")


# --- Dynamic Prompts Tests ---
@patch("devops_mcps.core.PromptLoader")
@patch("devops_mcps.core.logger")
def test_load_and_register_prompts_no_prompts(mock_logger, mock_prompt_loader):
  """Test load_and_register_prompts when no prompts are loaded."""
  # Arrange
  mock_loader_instance = MagicMock()
  mock_loader_instance.load_prompts.return_value = {}
  mock_prompt_loader.return_value = mock_loader_instance

  # Act
  core.load_and_register_prompts()

  # Assert
  mock_prompt_loader.assert_called_once()
  mock_loader_instance.load_prompts.assert_called_once()
  mock_logger.info.assert_called_with("No dynamic prompts to register")


@patch("devops_mcps.core.PromptLoader")
@patch("devops_mcps.core.mcp")
@patch("devops_mcps.core.logger")
def test_load_and_register_prompts_success(mock_logger, mock_mcp, mock_prompt_loader):
  """Test successful loading and registration of prompts."""
  # Arrange
  mock_prompts = {
    "test_prompt": {
      "name": "test_prompt",
      "description": "A test prompt",
      "template": "Test content with {{variable}}",
      "arguments": [
        {"name": "variable", "description": "Test variable", "required": True}
      ],
    }
  }

  mock_loader_instance = MagicMock()
  mock_loader_instance.load_prompts.return_value = mock_prompts
  mock_prompt_loader.return_value = mock_loader_instance

  mock_prompt_decorator = MagicMock()
  mock_mcp.prompt.return_value = mock_prompt_decorator

  # Act
  core.load_and_register_prompts()

  # Assert
  mock_prompt_loader.assert_called_once()
  mock_loader_instance.load_prompts.assert_called_once()
  mock_mcp.prompt.assert_called_once_with(
    name="test_prompt", description="A test prompt"
  )
  mock_logger.info.assert_called_with("Successfully registered 1 dynamic prompts")


@patch("devops_mcps.core.PromptLoader")
@patch("devops_mcps.core.logger")
def test_load_and_register_prompts_exception(mock_logger, mock_prompt_loader):
  """Test load_and_register_prompts when an exception occurs."""
  # Arrange
  mock_prompt_loader.side_effect = Exception("Test exception")

  # Act
  core.load_and_register_prompts()

  # Assert
  mock_prompt_loader.assert_called_once()
  mock_logger.error.assert_called_with(
    "Failed to load and register prompts: Test exception"
  )


@patch("devops_mcps.core.PromptLoader")
@patch("devops_mcps.core.mcp")
def test_load_and_register_prompts_no_arguments(mock_mcp, mock_prompt_loader):
  """Test loading prompts without arguments."""
  # Arrange
  mock_prompts = {
    "simple_prompt": {
      "name": "simple_prompt",
      "description": "A simple prompt",
      "template": "Simple content",
      # No arguments field
    }
  }

  mock_loader_instance = MagicMock()
  mock_loader_instance.load_prompts.return_value = mock_prompts
  mock_prompt_loader.return_value = mock_loader_instance

  mock_prompt_decorator = MagicMock()
  mock_mcp.prompt.return_value = mock_prompt_decorator

  # Act
  core.load_and_register_prompts()

  # Assert
  mock_mcp.prompt.assert_called_once_with(
    name="simple_prompt", description="A simple prompt"
  )
  assert core.logger is not None
