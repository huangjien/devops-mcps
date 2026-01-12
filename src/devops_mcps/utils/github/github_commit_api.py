"""GitHub Commit API functions.

This module contains functions for interacting with GitHub commits,
including listing commits from repositories.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from github import (
  GithubException,
  UnknownObjectException,
)
from github.PaginatedList import PaginatedList

from ...cache import cache
from ...inputs import ListCommitsInput
from .github_client import initialize_github_client
from .github_converters import _to_dict

logger = logging.getLogger(__name__)


def gh_list_commits(
  owner: str,
  repo: str,
  branch: Optional[str] = None,
  since: Optional[str] = None,
  until: Optional[str] = None,
  author: Optional[str] = None,
  path: Optional[str] = None,
  per_page: int = 30,
  page: int = 1,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for listing commits."""
  logger.debug(f"gh_list_commits called for {owner}/{repo}, branch: {branch}")

  # Check cache first
  branch_str = branch if branch else "default"
  cache_key = f"github:list_commits:{owner}/{repo}:{branch_str}:{since}:{until}:{author}:{path}:{per_page}:{page}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_list_commits: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = ListCommitsInput(
      owner=owner,
      repo=repo,
      branch=branch,
      since=since,
      until=until,
      author=author,
      path=path,
      per_page=per_page,
      page=page,
    )
    repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
    commit_kwargs: Dict[str, Any] = {}
    if input_data.branch:
      commit_kwargs["sha"] = input_data.branch
      logger.debug(f"Fetching commits for branch/sha: {input_data.branch}")
    else:
      logger.debug("Fetching commits for default branch.")

    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
      if not value:
        return None
      try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
      except ValueError:
        return None

    since_dt = _parse_iso_datetime(input_data.since)
    until_dt = _parse_iso_datetime(input_data.until)
    if since_dt:
      commit_kwargs["since"] = since_dt
    if until_dt:
      commit_kwargs["until"] = until_dt
    if input_data.author:
      commit_kwargs["author"] = input_data.author
    if input_data.path:
      commit_kwargs["path"] = input_data.path

    commits_paginated: PaginatedList = repo_obj.get_commits(**commit_kwargs)
    page_index = max(input_data.page - 1, 0)
    result = [_to_dict(item) for item in commits_paginated.get_page(page_index)]
    cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
    return result
  except UnknownObjectException:
    logger.warning(f"gh_list_commits: Repository '{owner}/{repo}' not found.")
    return {"error": f"Repository '{owner}/{repo}' not found."}
  except GithubException as e:
    msg = e.data.get("message", "Unknown GitHub error")
    logger.error(f"gh_list_commits GitHub Error: {e.status} - {e.data}", exc_info=True)
    if e.status == 409 and "Git Repository is empty" in msg:
      logger.warning(f"gh_list_commits: Repository '{owner}/{repo}' is empty.")
      return {"error": f"Repository {owner}/{repo} is empty."}
    # Handle case where branch doesn't exist (might also be UnknownObjectException or specific GithubException)
    if e.status == 404 or (e.status == 422 and "No commit found for SHA" in msg):
      logger.warning(f"Branch or SHA '{branch}' not found in {owner}/{repo}.")
      return {
        "error": f"Branch or SHA '{branch}' not found in repository {owner}/{repo}."
      }
    return {"error": f"GitHub API Error: {e.status} - {msg}"}
  except Exception as e:
    logger.error(f"Unexpected error in gh_list_commits: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
