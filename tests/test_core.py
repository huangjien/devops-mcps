import pytest
import sys
import os

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
