"""GitHub Issue API functions.

This module contains functions for interacting with GitHub issues,
including listing issues and getting issue details.
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
from ...inputs import ListIssuesInput
from .github_client import initialize_github_client
from .github_converters import _to_dict

logger = logging.getLogger(__name__)


def gh_list_issues(
  owner: str,
  repo: str,
  state: str = "open",
  labels: Optional[Union[str, List[str]]] = None,
  sort: str = "created",
  direction: str = "desc",
  since: Optional[str] = None,
  per_page: int = 30,
  page: int = 1,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for listing issues."""
  logger.debug(
    f"gh_list_issues called for {owner}/{repo}, state: {state}, labels: {labels}, sort: {sort}, direction: {direction}"
  )

  # Check cache first
  normalized_labels: Optional[List[str]]
  if isinstance(labels, str):
    normalized_labels = [x.strip() for x in labels.split(",") if x.strip()]
  else:
    normalized_labels = labels
  labels_str = ",".join(sorted(normalized_labels)) if normalized_labels else "none"
  cache_key = f"github:list_issues:{owner}/{repo}:{state}:{labels_str}:{sort}:{direction}:{since}:{per_page}:{page}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_list_issues: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = ListIssuesInput(
      owner=owner,
      repo=repo,
      state=state,
      labels=normalized_labels,
      sort=sort,
      direction=direction,
      since=since,
      per_page=per_page,
      page=page,
    )
    repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
    issue_kwargs: Dict[str, Any] = {
      "state": input_data.state,
      "sort": input_data.sort,
      "direction": input_data.direction,
    }
    if input_data.labels:
      issue_kwargs["labels"] = input_data.labels
      logger.debug(f"Filtering issues by labels: {input_data.labels}")

    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
      if not value:
        return None
      try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
      except ValueError:
        return None

    since_dt = _parse_iso_datetime(input_data.since)
    if since_dt:
      issue_kwargs["since"] = since_dt

    issues_paginated: PaginatedList = repo_obj.get_issues(**issue_kwargs)
    logger.debug(f"Found {issues_paginated.totalCount} issues matching criteria.")
    page_index = max(input_data.page - 1, 0)
    result = [_to_dict(item) for item in issues_paginated.get_page(page_index)]
    cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes
    return result
  except UnknownObjectException:
    logger.warning(f"gh_list_issues: Repository '{owner}/{repo}' not found.")
    return {"error": f"Repository '{owner}/{repo}' not found."}
  except GithubException as e:
    logger.error(f"gh_list_issues GitHub Error: {e.status} - {e.data}", exc_info=True)
    # Add specific error handling if needed, e.g., invalid labels
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_list_issues: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def gh_get_issue_details(owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
  """Fetches issue details including title, labels, timestamp, description, and comments.

  Args:
      owner: The owner of the repository.
      repo: The name of the repository.
      issue_number: The number of the issue.

  Returns:
      A dictionary containing issue details or an error message.
  """
  logger.debug(f"gh_get_issue_details called for {owner}/{repo} issue #{issue_number}")

  # Check cache first
  cache_key = f"github:issue_details:{owner}:{repo}:{issue_number}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_get_issue_details: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }

  try:
    issue_getter = getattr(github_client, "get_issue", None)
    if callable(issue_getter):
      issue = issue_getter(owner, repo, issue_number)
    else:
      repo_obj = github_client.get_repo(f"{owner}/{repo}")
      issue = repo_obj.get_issue(issue_number)
    comments = issue.get_comments()
    issue_details = {
      "title": issue.title,
      "labels": [label.name for label in issue.labels],
      "timestamp": issue.created_at.isoformat(),
      "description": issue.body,
      "comments": [comment.body for comment in comments],
    }
    logger.debug(
      f"Successfully retrieved issue details for {owner}/{repo} issue #{issue_number}"
    )
    cache.set(cache_key, issue_details, ttl=300)  # Cache for 5 minutes
    return issue_details
  except GithubException as e:
    logger.error(
      f"gh_get_issue_details GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_get_issue_details: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def gh_get_issue_content(owner: str, repo: str, issue_number: int) -> dict:
  """Fetches issue content including title, labels, timestamp, description, and comments.

  Args:
      owner: The owner of the repository.
      repo: The name of the repository.
      issue_number: The number of the issue.

  Returns:
      A dictionary containing issue content or an error message.
  """
  logger.debug(f"gh_get_issue_content called for {owner}/{repo} issue #{issue_number}")

  # Check cache first
  cache_key = f"github:issue_content:{owner}:{repo}:{issue_number}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_get_issue_content: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }

  try:
    repo_obj = github_client.get_repo(f"{owner}/{repo}")
    issue = repo_obj.get_issue(issue_number)
    comments = issue.get_comments()
    issue_content = {
      "title": issue.title,
      "labels": [label.name for label in issue.labels],
      "timestamp": issue.created_at.isoformat(),
      "description": issue.body,
      "comments": [comment.body for comment in comments],
    }
    logger.debug(
      f"Successfully retrieved issue content for {owner}/{repo} issue #{issue_number}"
    )
    cache.set(cache_key, issue_content, ttl=300)  # Cache for 5 minutes
    return issue_content
  except UnknownObjectException:
    logger.warning(
      f"gh_get_issue_content: Repository '{owner}/{repo}' or issue #{issue_number} not found."
    )
    return {"error": f"Repository '{owner}/{repo}' or issue #{issue_number} not found."}
  except GithubException as e:
    logger.error(
      f"gh_get_issue_content GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_get_issue_content: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
